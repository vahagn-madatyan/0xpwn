"""Tests for finding extraction from tool results and CVE enrichment orchestrator."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from oxpwn.core.models import Finding, Severity, ToolResult
from oxpwn.enrichment.cache import CveCache
from oxpwn.enrichment.enrichment import (
    CVE_REGEX,
    enrich_findings,
    extract_cve_ids,
    findings_from_tool_results,
)
from oxpwn.enrichment.nvd import NvdClient, NvdCveItem, extract_enrichment_data


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_tool_result(
    tool_name: str,
    parsed_output: dict | None = None,
) -> ToolResult:
    """Create a minimal ToolResult for testing."""
    return ToolResult(
        tool_name=tool_name,
        command=f"{tool_name} -test",
        stdout="",
        stderr="",
        exit_code=0,
        parsed_output=parsed_output,
        duration_ms=100,
    )


def _make_nvd_enrichment_data(
    *,
    cvss: float = 10.0,
    cwe_id: str = "CWE-502",
    description: str = "Remote code execution via Log4j JNDI lookup.",
) -> dict:
    """Create enrichment data matching extract_enrichment_data() shape."""
    return {
        "cvss": cvss,
        "cvss_severity": "CRITICAL",
        "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H",
        "cwe_id": cwe_id,
        "description": description,
        "references": ["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"],
    }


NUCLEI_PARSED_OUTPUT = {
    "count": 2,
    "findings": [
        {
            "template_id": "CVE-2021-44228",
            "name": "Apache Log4j RCE",
            "severity": "critical",
            "type": "http",
            "matched_at": "https://target.com/api",
            "host": "https://target.com",
            "url": "https://target.com/api",
            "description": "Remote code execution in Apache Log4j",
        },
        {
            "template_id": "tech-detect",
            "name": "Nginx Detection",
            "severity": "info",
            "type": "http",
            "matched_at": "https://target.com",
            "host": "https://target.com",
            "url": "https://target.com",
            "description": "Nginx web server detected",
        },
    ],
}

FFUF_PARSED_OUTPUT = {
    "count": 2,
    "findings": [
        {
            "position": 1,
            "url": "https://target.com/admin",
            "status": 200,
            "inputs": {"FUZZ": "admin"},
            "content_type": "text/html",
            "content_length": 1234,
        },
        {
            "position": 2,
            "url": "https://target.com/.env",
            "status": 403,
            "inputs": {"FUZZ": ".env"},
            "content_type": "text/plain",
            "content_length": 0,
        },
    ],
}

NMAP_PARSED_OUTPUT_WITH_SCRIPTS = {
    "hosts": [
        {
            "address": "192.168.1.1",
            "hostnames": ["target.local"],
            "status": "up",
            "ports": [
                {
                    "port_id": 443,
                    "protocol": "tcp",
                    "state": "open",
                    "service_name": "https",
                    "service_product": "nginx",
                    "service_version": "1.24",
                    "scripts": [
                        {
                            "id": "ssl-heartbleed",
                            "output": "VULNERABLE: CVE-2014-0160 The Heartbleed Bug",
                        }
                    ],
                },
                {
                    "port_id": 80,
                    "protocol": "tcp",
                    "state": "open",
                    "service_name": "http",
                    "service_product": "nginx",
                    "service_version": "1.24",
                    "scripts": [],
                },
            ],
        }
    ]
}

NMAP_PARSED_OUTPUT_PLAIN_PORTS = {
    "hosts": [
        {
            "address": "192.168.1.1",
            "hostnames": [],
            "status": "up",
            "ports": [
                {
                    "port_id": 22,
                    "protocol": "tcp",
                    "state": "open",
                    "service_name": "ssh",
                    "service_product": "OpenSSH",
                    "service_version": "8.9",
                    "scripts": [],
                },
                {
                    "port_id": 80,
                    "protocol": "tcp",
                    "state": "open",
                    "service_name": "http",
                    "service_product": "",
                    "service_version": "",
                    "scripts": [],
                },
            ],
        }
    ]
}


# ===================================================================
# CVE ID extraction tests
# ===================================================================


class TestExtractCveIds:
    """Tests for extract_cve_ids()."""

    def test_extract_from_nuclei_template_id(self) -> None:
        result = extract_cve_ids("CVE-2021-44228")
        assert result == ["CVE-2021-44228"]

    def test_extract_case_insensitive(self) -> None:
        result = extract_cve_ids("Found cve-2023-22515 in header")
        assert result == ["CVE-2023-22515"]

    def test_extract_multiple_cves(self) -> None:
        text = "Affected by CVE-2021-44228 and CVE-2023-22515 and cve-2014-0160"
        result = extract_cve_ids(text)
        assert result == ["CVE-2021-44228", "CVE-2023-22515", "CVE-2014-0160"]

    def test_normalize_to_uppercase(self) -> None:
        result = extract_cve_ids("cve-2021-44228")
        assert result == ["CVE-2021-44228"]

    def test_deduplication(self) -> None:
        text = "CVE-2021-44228 and cve-2021-44228 again"
        result = extract_cve_ids(text)
        assert result == ["CVE-2021-44228"]

    def test_no_match(self) -> None:
        result = extract_cve_ids("No vulnerabilities found here")
        assert result == []

    def test_empty_string(self) -> None:
        result = extract_cve_ids("")
        assert result == []

    def test_regex_pattern(self) -> None:
        """The regex handles 4+ digit suffixes."""
        assert extract_cve_ids("CVE-2023-12345") == ["CVE-2023-12345"]
        assert extract_cve_ids("CVE-2023-123456") == ["CVE-2023-123456"]
        # Too short (3 digits) should not match
        assert extract_cve_ids("CVE-2023-123") == []


# ===================================================================
# Finding extraction tests
# ===================================================================


class TestFindingsFromToolResults:
    """Tests for findings_from_tool_results()."""

    def test_nuclei_findings(self) -> None:
        tr = _make_tool_result("nuclei", NUCLEI_PARSED_OUTPUT)
        findings = findings_from_tool_results([tr])

        assert len(findings) == 2

        # First finding: CVE with critical severity
        f0 = findings[0]
        assert f0.title == "Apache Log4j RCE"
        assert f0.severity == Severity.critical
        assert f0.url == "https://target.com/api"
        assert f0.cve_id == "CVE-2021-44228"
        assert f0.evidence == "CVE-2021-44228"
        assert f0.tool_name == "nuclei"
        assert f0.description == "Remote code execution in Apache Log4j"

        # Second finding: info detection, no CVE
        f1 = findings[1]
        assert f1.title == "Nginx Detection"
        assert f1.severity == Severity.info
        assert f1.cve_id is None

    def test_ffuf_findings(self) -> None:
        tr = _make_tool_result("ffuf", FFUF_PARSED_OUTPUT)
        findings = findings_from_tool_results([tr])

        assert len(findings) == 2

        f0 = findings[0]
        assert f0.title == "Content discovered: https://target.com/admin"
        assert f0.severity == Severity.info
        assert f0.url == "https://target.com/admin"
        assert "200" in f0.description
        assert "text/html" in f0.description
        assert f0.tool_name == "ffuf"
        assert f0.cve_id is None

    def test_nmap_vuln_script_findings(self) -> None:
        tr = _make_tool_result("nmap", NMAP_PARSED_OUTPUT_WITH_SCRIPTS)
        findings = findings_from_tool_results([tr])

        # Only port 443 has scripts; port 80 has empty scripts → skipped
        assert len(findings) == 1

        f0 = findings[0]
        assert f0.title == "ssl-heartbleed"
        assert f0.severity == Severity.medium
        assert f0.url == "192.168.1.1:443/tcp"
        assert f0.cve_id == "CVE-2014-0160"
        assert "Heartbleed" in f0.description
        assert f0.tool_name == "nmap"

    def test_nmap_plain_ports_no_findings(self) -> None:
        """Open ports without vuln scripts produce no findings."""
        tr = _make_tool_result("nmap", NMAP_PARSED_OUTPUT_PLAIN_PORTS)
        findings = findings_from_tool_results([tr])
        assert findings == []

    def test_parsed_output_none_skipped(self) -> None:
        tr = _make_tool_result("nuclei", None)
        findings = findings_from_tool_results([tr])
        assert findings == []

    def test_unknown_tool_skipped(self) -> None:
        tr = _make_tool_result("unknown_tool", {"some": "data"})
        findings = findings_from_tool_results([tr])
        assert findings == []

    def test_mixed_tool_results(self) -> None:
        """Multiple tool results from different tools are all processed."""
        results = [
            _make_tool_result("nuclei", NUCLEI_PARSED_OUTPUT),
            _make_tool_result("ffuf", FFUF_PARSED_OUTPUT),
            _make_tool_result("nmap", NMAP_PARSED_OUTPUT_WITH_SCRIPTS),
        ]
        findings = findings_from_tool_results(results)
        # nuclei: 2, ffuf: 2, nmap: 1
        assert len(findings) == 5

        tool_names = [f.tool_name for f in findings]
        assert tool_names.count("nuclei") == 2
        assert tool_names.count("ffuf") == 2
        assert tool_names.count("nmap") == 1


# ===================================================================
# Enrichment orchestrator tests
# ===================================================================


class TestEnrichFindings:
    """Tests for enrich_findings() with mocked NvdClient and CveCache."""

    def _make_mock_client(
        self,
        cve_items: dict[str, NvdCveItem | None] | None = None,
    ) -> NvdClient:
        """Create a mock NvdClient that returns specified CVE items."""
        client = AsyncMock(spec=NvdClient)
        cve_items = cve_items or {}

        async def mock_fetch(cve_id: str) -> NvdCveItem | None:
            return cve_items.get(cve_id.upper())

        client.fetch_cve = AsyncMock(side_effect=mock_fetch)
        return client

    def _make_mock_cache(
        self,
        cached: dict[str, dict] | None = None,
    ) -> CveCache:
        """Create a mock CveCache with pre-loaded entries."""
        cache = MagicMock(spec=CveCache)
        cached = cached or {}

        def mock_get(cve_id: str) -> dict | None:
            return cached.get(cve_id.upper())

        cache.get = MagicMock(side_effect=mock_get)
        cache.put = MagicMock()
        return cache

    def test_finding_enriched_with_nvd_data(self) -> None:
        """Finding with CVE ID gets enriched with CVSS, CWE, remediation."""
        finding = Finding(
            title="Apache Log4j RCE",
            severity=Severity.critical,
            description="RCE via Log4j",
            url="https://target.com/api",
            evidence="CVE-2021-44228",
            tool_name="nuclei",
            cve_id="CVE-2021-44228",
        )

        enrichment_data = _make_nvd_enrichment_data()
        cache = self._make_mock_cache()
        client = self._make_mock_client()

        # Mock: cache miss, client returns data via extract_enrichment_data path
        # We simulate by making fetch_cve return a mock NvdCveItem,
        # but since we mock extract_enrichment_data, we patch it directly.
        with patch(
            "oxpwn.enrichment.enrichment.extract_enrichment_data",
            return_value=enrichment_data,
        ):
            # Make client.fetch_cve return a truthy mock object
            client.fetch_cve = AsyncMock(return_value=MagicMock(spec=NvdCveItem))

            result = asyncio.run(
                enrich_findings([finding], client, cache)
            )

        assert len(result) == 1
        assert result[0].cvss == 10.0
        assert result[0].cwe_id == "CWE-502"
        assert result[0].remediation == "Remote code execution via Log4j JNDI lookup."
        # Cache was populated
        cache.put.assert_called_once()

    def test_batch_dedup_same_cve(self) -> None:
        """Multiple findings referencing the same CVE → only one NVD fetch."""
        f1 = Finding(
            title="Log4j RCE Instance 1",
            severity=Severity.critical,
            description="First instance",
            url="https://a.com",
            evidence="CVE-2021-44228",
            tool_name="nuclei",
            cve_id="CVE-2021-44228",
        )
        f2 = Finding(
            title="Log4j RCE Instance 2",
            severity=Severity.critical,
            description="Second instance",
            url="https://b.com",
            evidence="CVE-2021-44228",
            tool_name="nuclei",
            cve_id="CVE-2021-44228",
        )

        enrichment_data = _make_nvd_enrichment_data()
        cache = self._make_mock_cache()
        client = self._make_mock_client()

        with patch(
            "oxpwn.enrichment.enrichment.extract_enrichment_data",
            return_value=enrichment_data,
        ):
            client.fetch_cve = AsyncMock(return_value=MagicMock(spec=NvdCveItem))

            asyncio.run(
                enrich_findings([f1, f2], client, cache)
            )

        # Only one fetch despite two findings referencing same CVE
        assert client.fetch_cve.call_count == 1
        # Both findings enriched
        assert f1.cvss == 10.0
        assert f2.cvss == 10.0

    def test_finding_without_cve_skipped(self) -> None:
        """Finding without any CVE reference is left unenriched."""
        finding = Finding(
            title="Nginx Detection",
            severity=Severity.info,
            description="Web server detected",
            url="https://target.com",
            evidence="tech-detect",
            tool_name="nuclei",
        )

        cache = self._make_mock_cache()
        client = self._make_mock_client()

        asyncio.run(
            enrich_findings([finding], client, cache)
        )

        assert finding.cvss is None
        assert finding.cwe_id is None
        assert finding.remediation is None
        # No NVD fetch attempted
        client.fetch_cve.assert_not_called()

    def test_nvd_error_graceful_degradation(self) -> None:
        """NVD client error for one CVE → that finding skipped, others enriched."""
        f_ok = Finding(
            title="Heartbleed",
            severity=Severity.high,
            description="OpenSSL vuln",
            url="https://target.com:443",
            evidence="ssl-heartbleed",
            tool_name="nmap",
            cve_id="CVE-2014-0160",
        )
        f_fail = Finding(
            title="Some Vuln",
            severity=Severity.medium,
            description="Another vuln",
            url="https://target.com",
            evidence="CVE-2099-9999",
            tool_name="nuclei",
            cve_id="CVE-2099-9999",
        )

        enrichment_data = _make_nvd_enrichment_data(
            cvss=7.5,
            cwe_id="CWE-119",
            description="OpenSSL heartbleed vulnerability",
        )
        cache = self._make_mock_cache()

        # Client: succeeds for one CVE, raises for another
        async def mock_fetch(cve_id: str) -> NvdCveItem | None:
            if cve_id == "CVE-2014-0160":
                return MagicMock(spec=NvdCveItem)
            raise RuntimeError("NVD API unavailable")

        client = AsyncMock(spec=NvdClient)
        client.fetch_cve = AsyncMock(side_effect=mock_fetch)

        with patch(
            "oxpwn.enrichment.enrichment.extract_enrichment_data",
            return_value=enrichment_data,
        ):
            asyncio.run(
                enrich_findings([f_ok, f_fail], client, cache)
            )

        # First finding enriched despite second failing
        assert f_ok.cvss == 7.5
        assert f_ok.cwe_id == "CWE-119"
        # Second finding left unenriched (error was caught)
        assert f_fail.cvss is None

    def test_cache_hit_avoids_api_call(self) -> None:
        """Cache hit for CVE → no NVD client fetch."""
        finding = Finding(
            title="Cached Vuln",
            severity=Severity.high,
            description="Already cached",
            url="https://target.com",
            evidence="CVE-2021-44228",
            tool_name="nuclei",
            cve_id="CVE-2021-44228",
        )

        enrichment_data = _make_nvd_enrichment_data()
        cache = self._make_mock_cache(cached={"CVE-2021-44228": enrichment_data})
        client = self._make_mock_client()

        asyncio.run(
            enrich_findings([finding], client, cache)
        )

        # Finding enriched from cache
        assert finding.cvss == 10.0
        assert finding.cwe_id == "CWE-502"
        # No NVD API call made
        client.fetch_cve.assert_not_called()
        # Cache.put not called (already cached)
        cache.put.assert_not_called()

    def test_end_to_end_pipeline(self) -> None:
        """Full pipeline: tool results → findings → enrichment."""
        # Create tool results
        nuclei_tr = _make_tool_result("nuclei", NUCLEI_PARSED_OUTPUT)
        nmap_tr = _make_tool_result("nmap", NMAP_PARSED_OUTPUT_WITH_SCRIPTS)

        # Convert to findings
        findings = findings_from_tool_results([nuclei_tr, nmap_tr])
        assert len(findings) == 3  # 2 nuclei + 1 nmap

        # CVE findings: Log4j (nuclei) and Heartbleed (nmap)
        cve_findings = [f for f in findings if f.cve_id is not None]
        assert len(cve_findings) == 2

        # Enrich
        enrichment_44228 = _make_nvd_enrichment_data()
        enrichment_0160 = _make_nvd_enrichment_data(
            cvss=7.5, cwe_id="CWE-119", description="Heartbleed bug"
        )

        cache = MagicMock(spec=CveCache)
        cache.get = MagicMock(return_value=None)  # All cache misses
        cache.put = MagicMock()

        call_count = {"n": 0}

        async def mock_fetch(cve_id: str) -> NvdCveItem | None:
            call_count["n"] += 1
            return MagicMock(spec=NvdCveItem)

        client = AsyncMock(spec=NvdClient)
        client.fetch_cve = AsyncMock(side_effect=mock_fetch)

        def mock_extract(cve_item: Any) -> dict:
            # Determine which CVE based on call order
            if mock_extract.call_count == 0:
                mock_extract.call_count += 1
                return enrichment_44228
            mock_extract.call_count += 1
            return enrichment_0160

        mock_extract.call_count = 0

        with patch(
            "oxpwn.enrichment.enrichment.extract_enrichment_data",
            side_effect=mock_extract,
        ):
            asyncio.run(
                enrich_findings(findings, client, cache)
            )

        # Exactly 2 API calls (one per unique CVE)
        assert client.fetch_cve.call_count == 2

        # Verify all CVE findings are enriched
        for f in findings:
            if f.cve_id is not None:
                assert f.cvss is not None, f"Finding {f.title} should have cvss"
                assert f.cwe_id is not None, f"Finding {f.title} should have cwe_id"
                assert f.remediation is not None, f"Finding {f.title} should have remediation"

        # Non-CVE finding (Nginx Detection) is untouched
        nginx = [f for f in findings if f.title == "Nginx Detection"][0]
        assert nginx.cvss is None
        assert nginx.cwe_id is None
