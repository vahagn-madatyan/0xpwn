"""Unit tests for the NVD CVE 2.0 API client."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from oxpwn.enrichment.nvd import (
    NvdClient,
    NvdCveItem,
    NvdCveResponse,
    extract_enrichment_data,
)

# ---------------------------------------------------------------------------
# Realistic NVD fixture — CVE-2021-44228 (Log4Shell) shape
# ---------------------------------------------------------------------------

CVE_2021_44228_FIXTURE: dict = {
    "resultsPerPage": 1,
    "startIndex": 0,
    "totalResults": 1,
    "vulnerabilities": [
        {
            "cve": {
                "id": "CVE-2021-44228",
                "descriptions": [
                    {
                        "lang": "en",
                        "value": (
                            "Apache Log4j2 2.0-beta9 through 2.15.0 (excluding security releases "
                            "2.12.2, 2.12.3, and 2.3.1) JNDI features used in configuration, log "
                            "messages, and parameters do not protect against attacker controlled "
                            "LDAP and other JNDI related endpoints."
                        ),
                    },
                ],
                "metrics": {
                    "cvssMetricV31": [
                        {
                            "source": "nvd@nist.gov",
                            "cvssData": {
                                "version": "3.1",
                                "vectorString": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
                                "baseScore": 10.0,
                                "baseSeverity": "CRITICAL",
                            },
                        }
                    ]
                },
                "weaknesses": [
                    {
                        "source": "nvd@nist.gov",
                        "type": "Primary",
                        "description": [{"lang": "en", "value": "CWE-917"}],
                    },
                ],
                "references": [
                    {"url": "https://logging.apache.org/log4j/2.x/security.html", "source": "nvd@nist.gov"},
                    {"url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog", "source": "nvd@nist.gov"},
                ],
            }
        }
    ],
}

# Fixture with only CVSS v3.0 (no v3.1)
CVE_V30_ONLY_FIXTURE: dict = {
    "resultsPerPage": 1,
    "startIndex": 0,
    "totalResults": 1,
    "vulnerabilities": [
        {
            "cve": {
                "id": "CVE-2020-99999",
                "descriptions": [{"lang": "en", "value": "Test vuln with only v3.0 score."}],
                "metrics": {
                    "cvssMetricV30": [
                        {
                            "source": "nvd@nist.gov",
                            "cvssData": {
                                "version": "3.0",
                                "vectorString": "CVSS:3.0/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N",
                                "baseScore": 7.5,
                                "baseSeverity": "HIGH",
                            },
                        }
                    ]
                },
                "weaknesses": [],
                "references": [],
            }
        }
    ],
}

# Fixture with only CVSS v2 (no v3.x)
CVE_V2_ONLY_FIXTURE: dict = {
    "resultsPerPage": 1,
    "startIndex": 0,
    "totalResults": 1,
    "vulnerabilities": [
        {
            "cve": {
                "id": "CVE-2015-00001",
                "descriptions": [{"lang": "en", "value": "Old vuln with only v2 score."}],
                "metrics": {
                    "cvssMetricV2": [
                        {
                            "source": "nvd@nist.gov",
                            "cvssData": {
                                "version": "2.0",
                                "vectorString": "AV:N/AC:L/Au:N/C:P/I:N/A:N",
                                "baseScore": 5.0,
                                "baseSeverity": "MEDIUM",
                            },
                        }
                    ]
                },
                "weaknesses": [],
                "references": [],
            }
        }
    ],
}

# Fixture with CWE placeholders that should be skipped
CVE_CWE_PLACEHOLDER_FIXTURE: dict = {
    "resultsPerPage": 1,
    "startIndex": 0,
    "totalResults": 1,
    "vulnerabilities": [
        {
            "cve": {
                "id": "CVE-2023-00001",
                "descriptions": [{"lang": "en", "value": "Vuln with placeholder CWE."}],
                "metrics": {"cvssMetricV31": [{"source": "nvd@nist.gov", "cvssData": {"version": "3.1", "vectorString": "", "baseScore": 6.0, "baseSeverity": "MEDIUM"}}]},
                "weaknesses": [
                    {
                        "source": "nvd@nist.gov",
                        "type": "Primary",
                        "description": [{"lang": "en", "value": "NVD-CWE-noinfo"}],
                    },
                    {
                        "source": "other",
                        "type": "Secondary",
                        "description": [{"lang": "en", "value": "NVD-CWE-Other"}],
                    },
                ],
                "references": [],
            }
        }
    ],
}

# Fixture with placeholder CWE first but real CWE second
CVE_CWE_MIXED_FIXTURE: dict = {
    "resultsPerPage": 1,
    "startIndex": 0,
    "totalResults": 1,
    "vulnerabilities": [
        {
            "cve": {
                "id": "CVE-2023-00002",
                "descriptions": [{"lang": "en", "value": "Vuln with mixed CWEs."}],
                "metrics": {},
                "weaknesses": [
                    {
                        "source": "nvd@nist.gov",
                        "type": "Primary",
                        "description": [{"lang": "en", "value": "NVD-CWE-noinfo"}],
                    },
                    {
                        "source": "other-source",
                        "type": "Secondary",
                        "description": [{"lang": "en", "value": "CWE-79"}],
                    },
                ],
                "references": [],
            }
        }
    ],
}


# ---------------------------------------------------------------------------
# Helper to create a mock httpx.Response
# ---------------------------------------------------------------------------

def _mock_response(status_code: int = 200, json_data: dict | None = None, text: str = "") -> httpx.Response:
    """Build a mock httpx.Response."""
    resp = httpx.Response(
        status_code=status_code,
        request=httpx.Request("GET", "https://example.com"),
    )
    if json_data is not None:
        resp._content = json.dumps(json_data).encode()
    else:
        resp._content = text.encode()
    return resp


# ---------------------------------------------------------------------------
# Tests: Pydantic model parsing
# ---------------------------------------------------------------------------


class TestNvdCveResponseParsing:
    def test_parse_cve_2021_44228(self):
        """CVE-2021-44228 fixture parses with correct CVSS 10.0 and CWE-917."""
        resp = NvdCveResponse.model_validate(CVE_2021_44228_FIXTURE)
        assert resp.total_results == 1
        assert len(resp.vulnerabilities) == 1

        cve = resp.vulnerabilities[0].cve
        assert cve.id == "CVE-2021-44228"
        assert len(cve.metrics.cvss_metric_v31) == 1
        assert cve.metrics.cvss_metric_v31[0].cvss_data.base_score == 10.0
        assert cve.metrics.cvss_metric_v31[0].cvss_data.base_severity == "CRITICAL"
        assert cve.weaknesses[0].description[0].value == "CWE-917"
        assert len(cve.references) == 2

    def test_parse_empty_response(self):
        """Empty NVD response parses with zero results."""
        resp = NvdCveResponse.model_validate(
            {"resultsPerPage": 0, "startIndex": 0, "totalResults": 0, "vulnerabilities": []}
        )
        assert resp.total_results == 0
        assert resp.vulnerabilities == []


# ---------------------------------------------------------------------------
# Tests: extract_enrichment_data
# ---------------------------------------------------------------------------


class TestExtractEnrichmentData:
    def test_cvss_v31_preferred(self):
        """CVSS v3.1 is preferred over v3.0 and v2."""
        cve = NvdCveResponse.model_validate(CVE_2021_44228_FIXTURE).vulnerabilities[0].cve
        data = extract_enrichment_data(cve)
        assert data["cvss"] == 10.0
        assert data["cvss_severity"] == "CRITICAL"
        assert "CVSS:3.1" in data["cvss_vector"]

    def test_cvss_v30_fallback(self):
        """Falls back to CVSS v3.0 when v3.1 is absent."""
        cve = NvdCveResponse.model_validate(CVE_V30_ONLY_FIXTURE).vulnerabilities[0].cve
        data = extract_enrichment_data(cve)
        assert data["cvss"] == 7.5
        assert data["cvss_severity"] == "HIGH"
        assert "CVSS:3.0" in data["cvss_vector"]

    def test_cvss_v2_fallback(self):
        """Falls back to CVSS v2 when both v3.x are absent."""
        cve = NvdCveResponse.model_validate(CVE_V2_ONLY_FIXTURE).vulnerabilities[0].cve
        data = extract_enrichment_data(cve)
        assert data["cvss"] == 5.0
        assert data["cvss_severity"] == "MEDIUM"

    def test_cwe_placeholder_filtering(self):
        """NVD-CWE-noinfo and NVD-CWE-Other are skipped."""
        cve = NvdCveResponse.model_validate(CVE_CWE_PLACEHOLDER_FIXTURE).vulnerabilities[0].cve
        data = extract_enrichment_data(cve)
        assert data["cwe_id"] is None

    def test_cwe_skips_placeholder_finds_real(self):
        """Placeholder CWEs are skipped but real CWE is found."""
        cve = NvdCveResponse.model_validate(CVE_CWE_MIXED_FIXTURE).vulnerabilities[0].cve
        data = extract_enrichment_data(cve)
        assert data["cwe_id"] == "CWE-79"

    def test_english_description_preferred(self):
        """English description is preferred."""
        cve = NvdCveResponse.model_validate(CVE_2021_44228_FIXTURE).vulnerabilities[0].cve
        data = extract_enrichment_data(cve)
        assert "Log4j2" in data["description"]

    def test_references_extracted(self):
        """Reference URLs are extracted."""
        cve = NvdCveResponse.model_validate(CVE_2021_44228_FIXTURE).vulnerabilities[0].cve
        data = extract_enrichment_data(cve)
        assert len(data["references"]) == 2
        assert any("logging.apache.org" in url for url in data["references"])


# ---------------------------------------------------------------------------
# Tests: NvdClient.fetch_cve
# ---------------------------------------------------------------------------


class TestNvdClientFetchCve:
    @pytest.fixture()
    def client_no_key(self) -> NvdClient:
        """Client without API key."""
        with patch.dict("os.environ", {}, clear=False):
            # Ensure NVD_API_KEY is not set
            env = dict(os.environ)
            env.pop("NVD_API_KEY", None)
            with patch.dict("os.environ", env, clear=True):
                return NvdClient()

    @pytest.fixture()
    def client_with_key(self) -> NvdClient:
        """Client with API key."""
        return NvdClient(api_key="test-key-12345")

    async def test_fetch_cve_success(self, client_no_key: NvdClient):
        """Successful fetch returns parsed NvdCveItem."""
        mock_resp = _mock_response(200, CVE_2021_44228_FIXTURE)
        client_no_key._client = AsyncMock()
        client_no_key._client.get = AsyncMock(return_value=mock_resp)
        client_no_key._last_request_time = 0.0  # skip rate limit wait

        result = await client_no_key.fetch_cve("CVE-2021-44228")

        assert result is not None
        assert result.id == "CVE-2021-44228"
        assert result.metrics.cvss_metric_v31[0].cvss_data.base_score == 10.0

    async def test_fetch_cve_404_returns_none(self, client_no_key: NvdClient):
        """404 response returns None."""
        mock_resp = _mock_response(404, text="Not Found")
        client_no_key._client = AsyncMock()
        client_no_key._client.get = AsyncMock(return_value=mock_resp)
        client_no_key._last_request_time = 0.0

        result = await client_no_key.fetch_cve("CVE-9999-99999")
        assert result is None

    async def test_fetch_cve_http_error_returns_none(self, client_no_key: NvdClient):
        """HTTP errors return None, never raise."""
        client_no_key._client = AsyncMock()
        client_no_key._client.get = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
        client_no_key._last_request_time = 0.0

        result = await client_no_key.fetch_cve("CVE-2021-44228")
        assert result is None

    async def test_fetch_cve_500_returns_none(self, client_no_key: NvdClient):
        """500 server error returns None."""
        mock_resp = _mock_response(500, text="Internal Server Error")
        client_no_key._client = AsyncMock()
        client_no_key._client.get = AsyncMock(return_value=mock_resp)
        client_no_key._last_request_time = 0.0

        result = await client_no_key.fetch_cve("CVE-2021-44228")
        assert result is None

    async def test_fetch_normalizes_cve_id_uppercase(self, client_no_key: NvdClient):
        """CVE ID is normalized to uppercase."""
        mock_resp = _mock_response(200, CVE_2021_44228_FIXTURE)
        client_no_key._client = AsyncMock()
        client_no_key._client.get = AsyncMock(return_value=mock_resp)
        client_no_key._last_request_time = 0.0

        await client_no_key.fetch_cve("cve-2021-44228")

        call_args = client_no_key._client.get.call_args
        assert call_args[1]["params"]["cveId"] == "CVE-2021-44228"


# ---------------------------------------------------------------------------
# Tests: API key header
# ---------------------------------------------------------------------------


class TestApiKeyHeader:
    def test_api_key_in_headers_when_provided(self):
        """API key appears in headers when provided."""
        client = NvdClient(api_key="my-secret-key")
        assert client._client.headers.get("apiKey") == "my-secret-key"
        assert client.has_api_key is True

    def test_no_api_key_header_when_not_provided(self):
        """No apiKey header when no key is provided."""
        with patch.dict("os.environ", {}, clear=True):
            client = NvdClient()
        assert "apiKey" not in client._client.headers
        assert client.has_api_key is False

    def test_api_key_from_env_var(self):
        """API key is read from NVD_API_KEY env var."""
        with patch.dict("os.environ", {"NVD_API_KEY": "env-key-789"}):
            client = NvdClient()
        assert client._client.headers.get("apiKey") == "env-key-789"
        assert client.has_api_key is True


# ---------------------------------------------------------------------------
# Tests: Rate limiter
# ---------------------------------------------------------------------------


class TestRateLimiter:
    async def test_rate_limiter_sleeps_without_key(self):
        """Rate limiter enforces 7s spacing without API key."""
        with patch.dict("os.environ", {}, clear=True):
            client = NvdClient()

        assert client._spacing == 7.0

        # Simulate a recent request
        import time
        client._last_request_time = time.monotonic()

        with patch("oxpwn.enrichment.nvd.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client._wait_for_rate_limit()
            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            assert 6.5 < sleep_time <= 7.0  # Should be close to 7s

    async def test_rate_limiter_sleeps_with_key(self):
        """Rate limiter enforces 0.6s spacing with API key."""
        client = NvdClient(api_key="test-key")
        assert client._spacing == 0.6

        import time
        client._last_request_time = time.monotonic()

        with patch("oxpwn.enrichment.nvd.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client._wait_for_rate_limit()
            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            assert 0.0 < sleep_time <= 0.6

    async def test_rate_limiter_no_sleep_when_enough_time_passed(self):
        """No sleep if enough time has already elapsed."""
        client = NvdClient(api_key="test-key")
        client._last_request_time = 0.0  # Far in the past

        with patch("oxpwn.enrichment.nvd.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await client._wait_for_rate_limit()
            mock_sleep.assert_not_called()


# ---------------------------------------------------------------------------
# Tests: search_cves
# ---------------------------------------------------------------------------


class TestSearchCves:
    async def test_search_returns_results(self):
        """Keyword search returns list of CVE items."""
        fixture = {
            "resultsPerPage": 2,
            "startIndex": 0,
            "totalResults": 2,
            "vulnerabilities": CVE_2021_44228_FIXTURE["vulnerabilities"] + CVE_V30_ONLY_FIXTURE["vulnerabilities"],
        }
        mock_resp = _mock_response(200, fixture)

        with patch.dict("os.environ", {}, clear=True):
            client = NvdClient()
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=mock_resp)
        client._last_request_time = 0.0

        results = await client.search_cves("log4j")
        assert len(results) == 2
        assert results[0].id == "CVE-2021-44228"

    async def test_search_error_returns_empty(self):
        """Search errors return empty list."""
        with patch.dict("os.environ", {}, clear=True):
            client = NvdClient()
        client._client = AsyncMock()
        client._client.get = AsyncMock(side_effect=httpx.ConnectError("timeout"))
        client._last_request_time = 0.0

        results = await client.search_cves("log4j")
        assert results == []

    async def test_search_passes_exact_match_param(self):
        """Exact match parameter is passed when exact=True."""
        mock_resp = _mock_response(200, {"resultsPerPage": 0, "startIndex": 0, "totalResults": 0, "vulnerabilities": []})

        with patch.dict("os.environ", {}, clear=True):
            client = NvdClient()
        client._client = AsyncMock()
        client._client.get = AsyncMock(return_value=mock_resp)
        client._last_request_time = 0.0

        await client.search_cves("log4j", exact=True)

        call_args = client._client.get.call_args
        assert "keywordExactMatch" in call_args[1]["params"]


# Need this import for the test with env patching
import os
