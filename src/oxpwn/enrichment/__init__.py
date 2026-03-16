"""CVE enrichment pipeline — NVD client, cache, and orchestration.

Public API:
    - ``enrich_findings()`` — batch-enrich Finding objects with NVD data
    - ``findings_from_tool_results()`` — convert tool parsed_output to Finding objects

Foundation:
    - ``NvdClient`` — async NVD CVE 2.0 API client with rate limiting
    - ``CveCache`` — SQLite CVE cache with TTL-based expiry
"""

from __future__ import annotations

from oxpwn.enrichment.cache import CveCache
from oxpwn.enrichment.enrichment import enrich_findings, findings_from_tool_results
from oxpwn.enrichment.nvd import NvdClient, extract_enrichment_data

__all__ = [
    "CveCache",
    "NvdClient",
    "enrich_findings",
    "extract_enrichment_data",
    "findings_from_tool_results",
]
