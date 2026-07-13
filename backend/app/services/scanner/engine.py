"""
Scanner Engine
==============

Orchestrates all sub-scanners:
  1. source_scanner  — regex + AST for .py/.java/.js/.ts/.cs and config files
  2. cert_scanner    — cryptography-library parse for .pem/.crt/.cer

Entry point: run_scan(file_map) → List[RawFinding]

file_map: {relative_path: bytes_content}

Design:
  - Pure function — no DB operations, no networking
  - Raises no exceptions to callers (errors logged, scan continues)
  - Per-file errors do not abort the whole scan
"""
from __future__ import annotations

import logging
from pathlib import Path

from app.services.scanner.source_scanner import RawFinding, scan_file
from app.services.scanner.cert_scanner import scan_cert_file

logger = logging.getLogger(__name__)

# Extensions handled by cert scanner
_CERT_EXTS = frozenset({".pem", ".crt", ".cer"})

# Extensions handled by source scanner
_SOURCE_EXTS = frozenset({
    ".py", ".java", ".js", ".ts", ".cs",
    ".json", ".yaml", ".yml", ".xml",
    ".properties", ".conf", ".config",
    # Also fall through for pem/crt so text patterns catch inline PEM in source
})


def run_scan(file_map: dict[str, bytes]) -> list[RawFinding]:
    """
    Scan all files in file_map.

    Args:
        file_map: {relative_path: content_bytes}

    Returns:
        Flat list of RawFinding from all files (no DB operations).
    """
    all_findings: list[RawFinding] = []

    for rel_path, content in file_map.items():
        ext = Path(rel_path).suffix.lower()
        file_findings: list[RawFinding] = []

        # Cert parser first (highest confidence)
        if ext in _CERT_EXTS:
            try:
                cert_findings = scan_cert_file(rel_path, content)
                file_findings.extend(cert_findings)
            except Exception as exc:
                logger.warning("cert_scanner error on %s: %s", rel_path, exc)

        # Source scanner for all supported text files
        # (includes .pem as text fallback; cert scanner took priority above)
        if ext in _SOURCE_EXTS or ext in _CERT_EXTS:
            try:
                src_findings = scan_file(rel_path, content)
                # If cert scan already produced findings for this file,
                # skip text-level findings that duplicate (same algo, no line)
                if file_findings:
                    cert_algos = {f.algorithm_family for f in file_findings}
                    src_findings = [
                        f for f in src_findings
                        if not (f.algorithm_family in cert_algos and f.line_number is None)
                    ]
                file_findings.extend(src_findings)
            except Exception as exc:
                logger.warning("source_scanner error on %s: %s", rel_path, exc)

        all_findings.extend(file_findings)

    return all_findings
