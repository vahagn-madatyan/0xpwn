"""Finding extraction from tool results and CVE enrichment orchestrator.

Bridges raw ``ToolResult`` objects (nuclei/ffuf/nmap) to enriched ``Finding``
objects with NVD-sourced CVE data (CVSS, CWE, remediation).
"""

from __future__ import annotations

import re
from typing import Any

import structlog

from oxpwn.core.models import Finding, Severity, ToolResult
from oxpwn.enrichment.cache import CveCache
from oxpwn.enrichment.nvd import NvdClient, extract_enrichment_data

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# CVE ID extraction
# ---------------------------------------------------------------------------

CVE_REGEX = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)


def extract_cve_ids(text: str) -> list[str]:
    """Extract all CVE IDs from *text*, normalized to uppercase and deduplicated.

    Preserves discovery order.
    """
    seen: set[str] = set()
    result: list[str] = []
    for match in CVE_REGEX.findall(text):
        upper = match.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(upper)
    return result


# ---------------------------------------------------------------------------
# Severity mapping helpers
# ---------------------------------------------------------------------------

_NUCLEI_SEVERITY_MAP: dict[str, Severity] = {
    "critical": Severity.critical,
    "high": Severity.high,
    "medium": Severity.medium,
    "low": Severity.low,
    "info": Severity.info,
    "unknown": Severity.info,
}


def _map_nuclei_severity(raw: str | None) -> Severity:
    """Map nuclei severity string to ``Severity`` enum, defaulting to info."""
    if not raw:
        return Severity.info
    return _NUCLEI_SEVERITY_MAP.get(raw.lower(), Severity.info)


# ---------------------------------------------------------------------------
# Tool result → Finding converters
# ---------------------------------------------------------------------------


def _findings_from_nuclei(parsed: dict[str, Any]) -> list[Finding]:
    """Convert nuclei ``parsed_output`` to a list of ``Finding`` objects."""
    findings: list[Finding] = []
    for entry in parsed.get("findings", []):
        template_id = entry.get("template_id", "")
        name = entry.get("name") or template_id
        url = entry.get("matched_at") or entry.get("url") or ""
        description = entry.get("description") or ""
        severity = _map_nuclei_severity(entry.get("severity"))

        # Extract CVE from template_id (e.g. "CVE-2021-44228")
        cve_ids = extract_cve_ids(template_id)
        cve_id = cve_ids[0] if cve_ids else None

        findings.append(
            Finding(
                title=name,
                severity=severity,
                description=description,
                url=url,
                evidence=template_id,
                tool_name="nuclei",
                cve_id=cve_id,
            )
        )
    return findings


def _findings_from_ffuf(parsed: dict[str, Any]) -> list[Finding]:
    """Convert ffuf ``parsed_output`` to a list of ``Finding`` objects."""
    findings: list[Finding] = []
    for entry in parsed.get("findings", []):
        url = entry.get("url", "")
        status = entry.get("status", 0)
        content_type = entry.get("content_type", "unknown")
        inputs = entry.get("inputs", {})

        findings.append(
            Finding(
                title=f"Content discovered: {url}",
                severity=Severity.info,
                description=f"HTTP {status} response (content-type: {content_type})",
                url=url,
                evidence=str(inputs) if inputs else "",
                tool_name="ffuf",
            )
        )
    return findings


def _findings_from_nmap(parsed: dict[str, Any]) -> list[Finding]:
    """Convert nmap ``parsed_output`` to ``Finding`` objects.

    Only ports with vulnerability-relevant script output produce findings.
    Plain open-port/service entries are not vulnerability signals and are skipped.
    """
    findings: list[Finding] = []
    for host in parsed.get("hosts", []):
        address = host.get("address", "")
        for port_entry in host.get("ports", []):
            scripts = port_entry.get("scripts", [])
            if not scripts:
                continue  # No vuln signal — skip plain port entries

            port_id = port_entry.get("port_id", 0)
            protocol = port_entry.get("protocol", "tcp")

            for script in scripts:
                script_id = script.get("id", "unknown-script")
                script_output = script.get("output", "")

                # Extract CVE IDs from script output
                cve_ids = extract_cve_ids(script_output)
                cve_id = cve_ids[0] if cve_ids else None

                findings.append(
                    Finding(
                        title=script_id,
                        severity=Severity.medium,
                        description=script_output,
                        url=f"{address}:{port_id}/{protocol}",
                        evidence=script_output,
                        tool_name="nmap",
                        cve_id=cve_id,
                    )
                )
    return findings


# Dispatcher: tool_name → converter
_TOOL_CONVERTERS: dict[str, Any] = {
    "nuclei": _findings_from_nuclei,
    "ffuf": _findings_from_ffuf,
    "nmap": _findings_from_nmap,
}


def findings_from_tool_results(tool_results: list[ToolResult]) -> list[Finding]:
    """Convert a list of ``ToolResult`` objects into ``Finding`` objects.

    Dispatches to tool-specific converters for nuclei, ffuf, and nmap.
    Skips tool results with ``parsed_output is None`` or unknown tool names.
    """
    findings: list[Finding] = []
    for tr in tool_results:
        if tr.parsed_output is None:
            logger.debug("enrichment.skipped_no_output", tool_name=tr.tool_name)
            continue

        converter = _TOOL_CONVERTERS.get(tr.tool_name)
        if converter is None:
            logger.debug("enrichment.skipped_unknown_tool", tool_name=tr.tool_name)
            continue

        try:
            findings.extend(converter(tr.parsed_output))
        except Exception:
            logger.warning(
                "enrichment.conversion_error",
                tool_name=tr.tool_name,
                exc_info=True,
            )
    return findings


# ---------------------------------------------------------------------------
# CVE enrichment orchestrator
# ---------------------------------------------------------------------------


async def enrich_findings(
    findings: list[Finding],
    client: NvdClient,
    cache: CveCache,
) -> list[Finding]:
    """Batch-enrich findings with NVD CVE data.

    For each finding, collects CVE IDs from ``cve_id``, ``title``,
    ``description``, and ``evidence`` fields.  Deduplicates CVE IDs across
    all findings, resolves each via cache-then-NVD-client, and populates
    ``cvss``, ``cwe_id``, and ``remediation`` on matching findings.

    Errors are logged per-finding and never crash the pipeline.
    Returns the same list (mutated in-place).
    """
    # Phase 1: Collect all CVE IDs across all findings
    cve_to_findings: dict[str, list[Finding]] = {}
    for finding in findings:
        text_fields = " ".join(
            f
            for f in [finding.cve_id, finding.title, finding.description, finding.evidence]
            if f
        )
        cve_ids = extract_cve_ids(text_fields)
        for cve_id in cve_ids:
            cve_to_findings.setdefault(cve_id, []).append(finding)

    unique_cve_ids = list(cve_to_findings.keys())
    if not unique_cve_ids:
        logger.debug("enrichment.no_cves_found", finding_count=len(findings))
        return findings

    logger.info(
        "enrichment.resolving_cves",
        unique_cve_count=len(unique_cve_ids),
        finding_count=len(findings),
    )

    # Phase 2: Resolve each unique CVE ID (cache first, then API)
    resolved: dict[str, dict[str, Any]] = {}
    for cve_id in unique_cve_ids:
        try:
            # Check cache first
            cached = cache.get(cve_id)
            if cached is not None:
                resolved[cve_id] = cached
                continue

            # Fetch from NVD API
            cve_item = await client.fetch_cve(cve_id)
            if cve_item is None:
                logger.debug("enrichment.cve_not_found", cve_id=cve_id)
                continue

            enrichment_data = extract_enrichment_data(cve_item)
            cache.put(cve_id, enrichment_data)
            resolved[cve_id] = enrichment_data
            logger.debug("enrichment.cve_extracted", cve_id=cve_id)

        except Exception:
            logger.warning(
                "enrichment.cve_resolve_error",
                cve_id=cve_id,
                exc_info=True,
            )

    # Phase 3: Apply enrichment data to findings
    for cve_id, affected_findings in cve_to_findings.items():
        data = resolved.get(cve_id)
        if data is None:
            for f in affected_findings:
                logger.debug("enrichment.skipped", title=f.title, reason="cve_unresolved")
            continue

        for finding in affected_findings:
            try:
                if data.get("cvss") is not None:
                    finding.cvss = data["cvss"]
                if data.get("cwe_id") is not None:
                    finding.cwe_id = data["cwe_id"]
                if data.get("description") is not None:
                    finding.remediation = data["description"]
                if finding.cve_id is None:
                    finding.cve_id = cve_id

                logger.debug(
                    "enrichment.finding_enriched",
                    title=finding.title,
                    cve_id=cve_id,
                    cvss=finding.cvss,
                )
            except Exception:
                logger.warning(
                    "enrichment.apply_error",
                    title=finding.title,
                    cve_id=cve_id,
                    exc_info=True,
                )

    return findings
