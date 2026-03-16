"""Async NVD CVE 2.0 API client with rate limiting and Pydantic response models."""

from __future__ import annotations

import asyncio
import os
import time
from typing import Any

import httpx
import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# NVD CVE 2.0 Response Models (enrichment-relevant subset)
# ---------------------------------------------------------------------------

_NVD_BASE_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"

# Rate-limit spacing: stay safely under NVD limits.
# Without API key: 5 req / 30s → 7s between requests.
# With API key:   50 req / 30s → 0.6s between requests.
_SPACING_NO_KEY = 7.0
_SPACING_WITH_KEY = 0.6


class NvdCvssData(BaseModel):
    """CVSS score data from NVD metrics."""

    version: str = ""
    vector_string: str = Field("", alias="vectorString")
    base_score: float = Field(0.0, alias="baseScore")
    base_severity: str = Field("", alias="baseSeverity")


class NvdCvssMetric(BaseModel):
    """A single CVSS metric entry (wraps cvssData)."""

    source: str = ""
    cvss_data: NvdCvssData = Field(default_factory=NvdCvssData, alias="cvssData")


class NvdWeaknessDescription(BaseModel):
    """A single CWE description entry."""

    lang: str = ""
    value: str = ""


class NvdWeakness(BaseModel):
    """Weakness (CWE) block from NVD."""

    source: str = ""
    type: str = ""
    description: list[NvdWeaknessDescription] = Field(default_factory=list)


class NvdDescription(BaseModel):
    """Description entry from NVD CVE."""

    lang: str = ""
    value: str = ""


class NvdReference(BaseModel):
    """Reference URL entry from NVD CVE."""

    url: str = ""
    source: str = ""


class NvdCveMetrics(BaseModel):
    """Metrics block containing CVSS v3.1, v3.0, and v2 arrays."""

    cvss_metric_v31: list[NvdCvssMetric] = Field(default_factory=list, alias="cvssMetricV31")
    cvss_metric_v30: list[NvdCvssMetric] = Field(default_factory=list, alias="cvssMetricV30")
    cvss_metric_v2: list[NvdCvssMetric] = Field(default_factory=list, alias="cvssMetricV2")


class NvdCveItem(BaseModel):
    """Core CVE item from the NVD response."""

    id: str = ""
    descriptions: list[NvdDescription] = Field(default_factory=list)
    metrics: NvdCveMetrics = Field(default_factory=NvdCveMetrics)
    weaknesses: list[NvdWeakness] = Field(default_factory=list)
    references: list[NvdReference] = Field(default_factory=list)


class NvdVulnerability(BaseModel):
    """Wrapper: each entry in the vulnerabilities array."""

    cve: NvdCveItem = Field(default_factory=NvdCveItem)


class NvdCveResponse(BaseModel):
    """Top-level NVD CVE 2.0 API response."""

    results_per_page: int = Field(0, alias="resultsPerPage")
    start_index: int = Field(0, alias="startIndex")
    total_results: int = Field(0, alias="totalResults")
    vulnerabilities: list[NvdVulnerability] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# CWE placeholder values to skip
# ---------------------------------------------------------------------------
_CWE_PLACEHOLDERS = frozenset({"NVD-CWE-noinfo", "NVD-CWE-Other"})


# ---------------------------------------------------------------------------
# Enrichment data extractor
# ---------------------------------------------------------------------------


def extract_enrichment_data(cve: NvdCveItem) -> dict[str, Any]:
    """Extract enrichment-relevant data from a parsed NVD CVE item.

    Returns a flat dict with keys: cvss, cvss_severity, cvss_vector, cwe_id,
    description, references.  CVSS uses v3.1 → v3.0 → v2 fallback chain.
    CWE skips NVD placeholder values.
    """
    data: dict[str, Any] = {
        "cvss": None,
        "cvss_severity": None,
        "cvss_vector": None,
        "cwe_id": None,
        "description": None,
        "references": [],
    }

    # --- CVSS: prefer v3.1, then v3.0, then v2 ---
    cvss_metric: NvdCvssMetric | None = None
    if cve.metrics.cvss_metric_v31:
        cvss_metric = cve.metrics.cvss_metric_v31[0]
    elif cve.metrics.cvss_metric_v30:
        cvss_metric = cve.metrics.cvss_metric_v30[0]
    elif cve.metrics.cvss_metric_v2:
        cvss_metric = cve.metrics.cvss_metric_v2[0]

    if cvss_metric:
        data["cvss"] = cvss_metric.cvss_data.base_score
        data["cvss_severity"] = cvss_metric.cvss_data.base_severity
        data["cvss_vector"] = cvss_metric.cvss_data.vector_string

    # --- CWE: first non-placeholder from any weakness block ---
    for weakness in cve.weaknesses:
        for desc in weakness.description:
            if desc.value and desc.value not in _CWE_PLACEHOLDERS:
                data["cwe_id"] = desc.value
                break
        if data["cwe_id"]:
            break

    # --- Description: prefer English ---
    for desc in cve.descriptions:
        if desc.lang == "en":
            data["description"] = desc.value
            break
    if not data["description"] and cve.descriptions:
        data["description"] = cve.descriptions[0].value

    # --- References ---
    data["references"] = [ref.url for ref in cve.references if ref.url]

    return data


# ---------------------------------------------------------------------------
# NVD Client
# ---------------------------------------------------------------------------


class NvdClient:
    """Async NVD CVE 2.0 API client with rate limiting.

    Parameters
    ----------
    api_key:
        NVD API key.  Falls back to ``NVD_API_KEY`` env var if not provided.
    base_url:
        Override the NVD base URL (useful for testing).
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key or os.environ.get("NVD_API_KEY")
        self._base_url = base_url or _NVD_BASE_URL

        headers: dict[str, str] = {"Accept": "application/json"}
        if self._api_key:
            headers["apiKey"] = self._api_key

        self._client = httpx.AsyncClient(
            headers=headers,
            timeout=30.0,
        )

        self._spacing = _SPACING_WITH_KEY if self._api_key else _SPACING_NO_KEY
        self._last_request_time: float = 0.0

    @property
    def has_api_key(self) -> bool:
        """Whether an API key is configured."""
        return self._api_key is not None

    # -- Rate limiter -------------------------------------------------------

    async def _wait_for_rate_limit(self) -> None:
        """Sleep if needed to respect NVD rate limits."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self._spacing:
            wait_time = self._spacing - elapsed
            logger.debug("nvd.rate_limited", wait_seconds=round(wait_time, 2))
            await asyncio.sleep(wait_time)
        self._last_request_time = time.monotonic()

    # -- API methods --------------------------------------------------------

    async def fetch_cve(self, cve_id: str) -> NvdCveItem | None:
        """Fetch a single CVE by ID.  Returns None on 404 or errors."""
        cve_id = cve_id.upper().strip()
        await self._wait_for_rate_limit()

        try:
            resp = await self._client.get(
                self._base_url,
                params={"cveId": cve_id},
            )
        except httpx.HTTPError as exc:
            logger.warning(
                "nvd.fetch_error",
                cve_id=cve_id,
                error=str(exc),
            )
            return None

        if resp.status_code == 404:
            logger.debug("nvd.fetch", cve_id=cve_id, status=404)
            return None

        if resp.status_code != 200:
            logger.warning(
                "nvd.fetch_error",
                cve_id=cve_id,
                status=resp.status_code,
                body_head=resp.text[:200],
            )
            return None

        logger.debug("nvd.fetch", cve_id=cve_id, status=200)

        try:
            parsed = NvdCveResponse.model_validate(resp.json())
        except Exception as exc:
            logger.warning(
                "nvd.fetch_error",
                cve_id=cve_id,
                error=f"parse_error: {exc}",
            )
            return None

        if not parsed.vulnerabilities:
            return None

        return parsed.vulnerabilities[0].cve

    async def search_cves(
        self,
        keyword: str,
        *,
        exact: bool = True,
    ) -> list[NvdCveItem]:
        """Search CVEs by keyword.  Returns list of CVE items."""
        await self._wait_for_rate_limit()

        params: dict[str, str] = {"keywordSearch": keyword}
        if exact:
            params["keywordExactMatch"] = ""

        try:
            resp = await self._client.get(self._base_url, params=params)
        except httpx.HTTPError as exc:
            logger.warning(
                "nvd.fetch_error",
                keyword=keyword,
                error=str(exc),
            )
            return []

        if resp.status_code != 200:
            logger.warning(
                "nvd.fetch_error",
                keyword=keyword,
                status=resp.status_code,
                body_head=resp.text[:200],
            )
            return []

        logger.debug("nvd.fetch", keyword=keyword, status=200)

        try:
            parsed = NvdCveResponse.model_validate(resp.json())
        except Exception as exc:
            logger.warning(
                "nvd.fetch_error",
                keyword=keyword,
                error=f"parse_error: {exc}",
            )
            return []

        return [v.cve for v in parsed.vulnerabilities]

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> NvdClient:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()
