"""
Source Code Scanner
===================

Scans text-based source files (.py, .java, .js, .ts, .cs, and config formats)
for cryptographic API usage using:

  1. Rule-registry regex matching per line
  2. Python AST analysis for higher-confidence Python findings
  3. Evidence masking — never stores full private keys or secrets

Architecture:
  - scan_file(path, content) → List[RawFinding]
  - Python files get both regex AND AST passes; AST findings shadow/upgrade regex
  - All other languages get the regex pass only

False-positive guards:
  - Comment-only lines are down-scored (confidence *= 0.5)
  - Negative-pattern hit cancels the match entirely
  - Bare word matches in pure comment lines are skipped for low-confidence rules
"""
from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from app.services.scanner.rules import (
    CompiledRule,
    Category,
    QuantumStatus,
    get_rules_for_extension,
)

# ---------------------------------------------------------------------------
# Shared output dataclass
# ---------------------------------------------------------------------------

@dataclass
class RawFinding:
    """Intermediate finding before DB persistence."""
    rule_id: str
    algorithm: str
    algorithm_family: str
    category: Category
    quantum_status: QuantumStatus
    file_path: str               # relative path inside the archive / upload
    line_number: int | None
    evidence: str                # masked snippet
    confidence: float
    key_size: int | None = None
    usage_context: str | None = None
    detection_method: str = "regex"
    nist_recommendation: str = ""
    legacy_security_note: str = ""


# ---------------------------------------------------------------------------
# Evidence masking
# ---------------------------------------------------------------------------

_PEM_BODY_RE = re.compile(r"(?<=-----)\s*[A-Za-z0-9+/=\s]{20,}(?=\s*-----)", re.S)
_KEY_BYTES_RE = re.compile(r"(0x[0-9a-fA-F]{16,})", re.I)


def _mask_evidence(line: str) -> str:
    """Strip sensitive key material; keep the structural pattern."""
    masked = line.strip()
    # Mask inline PEM body bytes
    masked = _PEM_BODY_RE.sub(" <KEY_MATERIAL_REDACTED> ", masked)
    # Mask long hex literals
    masked = _KEY_BYTES_RE.sub(r"<0xHEX_REDACTED>", masked)
    # Truncate very long lines
    if len(masked) > 200:
        masked = masked[:200] + "…"
    return masked


# ---------------------------------------------------------------------------
# Comment detection per language
# ---------------------------------------------------------------------------

_COMMENT_PATTERNS: dict[str, re.Pattern] = {
    ".py":   re.compile(r"^\s*#"),
    ".java": re.compile(r"^\s*//|^\s*\*"),
    ".js":   re.compile(r"^\s*//|^\s*\*"),
    ".ts":   re.compile(r"^\s*//|^\s*\*"),
    ".cs":   re.compile(r"^\s*//|^\s*\*"),
    ".yaml": re.compile(r"^\s*#"),
    ".yml":  re.compile(r"^\s*#"),
    ".properties": re.compile(r"^\s*#|^\s*!"),
    ".conf": re.compile(r"^\s*#|^\s*;"),
    ".config": re.compile(r"^\s*<!--"),
    ".xml":  re.compile(r"^\s*<!--"),
}


def _is_comment_line(line: str, ext: str) -> bool:
    pat = _COMMENT_PATTERNS.get(ext)
    return bool(pat and pat.match(line))


# ---------------------------------------------------------------------------
# Regex-based scan (all text languages)
# ---------------------------------------------------------------------------

def _regex_scan_lines(
    lines: list[str],
    ext: str,
    rel_path: str,
    rules: list[CompiledRule],
) -> list[RawFinding]:
    findings: list[RawFinding] = []
    is_comment_fn = _COMMENT_PATTERNS.get(ext)

    for lineno, line in enumerate(lines, start=1):
        if not line.strip():
            continue

        in_comment = bool(is_comment_fn and is_comment_fn.match(line))

        for cr in rules:
            rule = cr.rule

            # Check at least one positive pattern matches
            matched = False
            for pat in cr.compiled_patterns:
                if pat.search(line):
                    matched = True
                    break
            if not matched:
                continue

            # Check no negative patterns match
            neg_hit = any(np.search(line) for np in cr.compiled_negative)
            if neg_hit:
                continue

            # Set confidence — reduce for comment lines
            conf = rule.base_confidence
            if in_comment:
                # Down-score comments; skip entirely for low-base rules
                conf *= 0.4
                if conf < 0.25:
                    continue

            findings.append(RawFinding(
                rule_id=rule.id,
                algorithm=rule.algorithm,
                algorithm_family=rule.algorithm_family,
                category=rule.category,
                quantum_status=rule.quantum_status,
                file_path=rel_path,
                line_number=lineno,
                evidence=_mask_evidence(line),
                confidence=round(conf, 3),
                detection_method="regex",
                nist_recommendation=rule.nist_recommendation,
                legacy_security_note=rule.legacy_security_note,
            ))

    return findings


# ---------------------------------------------------------------------------
# Python AST analysis
# ---------------------------------------------------------------------------

_AST_CRYPTO_LIBS = {
    "cryptography", "Crypto", "OpenSSL", "ssl", "hashlib",
    "hmac", "rsa", "ecdsa", "paramiko", "bcrypt", "nacl", "pyca",
}

_AST_ALGO_MAP: dict[str, tuple[str, str, Category, QuantumStatus]] = {
    # (algorithm, family, category, quantum_status)
    "RSA":          ("RSA",               "RSA",      Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "rsa":          ("RSA",               "RSA",      Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "ECDSA":        ("ECDSA",             "ECDSA",    Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "ECDH":         ("ECDH",              "ECDH",     Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "ECC":          ("ECC",               "ECC",      Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "ec":           ("ECC",               "ECC",      Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "dsa":          ("DSA",               "DSA",      Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "DSA":          ("DSA",               "DSA",      Category.QUANTUM_VULNERABLE_PUBLIC_KEY, QuantumStatus.vulnerable),
    "AES":          ("AES",               "AES",      Category.SYMMETRIC,                      QuantumStatus.safe),
    "ChaCha20":     ("ChaCha20-Poly1305", "ChaCha20", Category.SYMMETRIC,                      QuantumStatus.safe),
    "Poly1305":     ("ChaCha20-Poly1305", "ChaCha20", Category.SYMMETRIC,                      QuantumStatus.safe),
    "md5":          ("MD5",               "MD5",      Category.LEGACY_DEPRECATED,              QuantumStatus.deprecated),
    "MD5":          ("MD5",               "MD5",      Category.LEGACY_DEPRECATED,              QuantumStatus.deprecated),
    "sha1":         ("SHA-1",             "SHA-1",    Category.LEGACY_DEPRECATED,              QuantumStatus.deprecated),
    "SHA1":         ("SHA-1",             "SHA-1",    Category.LEGACY_DEPRECATED,              QuantumStatus.deprecated),
    "sha256":       ("SHA-256",           "SHA-2",    Category.HASH,                           QuantumStatus.borderline),
    "sha384":       ("SHA-384",           "SHA-2",    Category.HASH,                           QuantumStatus.safe),
    "sha512":       ("SHA-512",           "SHA-2",    Category.HASH,                           QuantumStatus.safe),
    "sha3_256":     ("SHA-3-256",         "SHA-3",    Category.HASH,                           QuantumStatus.safe),
    "sha3_512":     ("SHA-3-512",         "SHA-3",    Category.HASH,                           QuantumStatus.safe),
}

_HASHLIB_NAMES = {"md5", "sha1", "sha224", "sha256", "sha384", "sha512",
                  "sha3_224", "sha3_256", "sha3_384", "sha3_512", "blake2b", "blake2s"}


def _ast_scan(source: str, rel_path: str) -> list[RawFinding]:
    """High-confidence Python AST analysis."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    findings: list[RawFinding] = []

    class CryptoVisitor(ast.NodeVisitor):
        def _emit(self, node: ast.AST, algo: str, family: str,
                  cat: Category, qstatus: QuantumStatus,
                  ctx: str | None = None, evidence: str = "") -> None:
            lineno = getattr(node, "lineno", None)
            findings.append(RawFinding(
                rule_id=f"AST-{algo.upper().replace('-', '_')}",
                algorithm=algo,
                algorithm_family=family,
                category=cat,
                quantum_status=qstatus,
                file_path=rel_path,
                line_number=lineno,
                evidence=_mask_evidence(evidence or algo),
                confidence=0.92,
                usage_context=ctx,
                detection_method="ast",
                nist_recommendation="",
            ))

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top in _AST_CRYPTO_LIBS:
                    pass  # Don't emit on bare import; wait for attribute usage
            self.generic_visit(node)

        def visit_Call(self, node: ast.Call) -> None:
            """Detect: hashlib.sha1(), Cipher.new(AES.MODE_GCM), rsa.generate(), etc."""
            src = ast.unparse(node) if hasattr(ast, "unparse") else ""

            # hashlib.X(...)
            if isinstance(node.func, ast.Attribute):
                attr = node.func.attr
                parent = ""
                if isinstance(node.func.value, ast.Name):
                    parent = node.func.value.id
                elif isinstance(node.func.value, ast.Attribute):
                    parent = node.func.value.attr

                if parent == "hashlib" and attr in _HASHLIB_NAMES:
                    info = _AST_ALGO_MAP.get(attr)
                    if info:
                        self._emit(node, info[0], info[1], info[2], info[3],
                                   ctx="hash", evidence=src[:120])

                # X.generate_private_key() / X.generate() — RSA, DSA, EC
                if attr in ("generate_private_key", "generate", "generate_parameters",
                             "new_key", "newkeys"):
                    info = _AST_ALGO_MAP.get(parent)
                    if info:
                        self._emit(node, info[0], info[1], info[2], info[3],
                                   ctx="key_generation", evidence=src[:120])

                # Cipher.getInstance("AES/GCM/...") — JVM style in Jython or native
                if attr == "getInstance" and parent == "Cipher":
                    if node.args:
                        try:
                            algo_str = ast.literal_eval(node.args[0])
                            if isinstance(algo_str, str):
                                for k, v in _AST_ALGO_MAP.items():
                                    if k.upper() in algo_str.upper():
                                        self._emit(node, v[0], v[1], v[2], v[3],
                                                   ctx="cipher_init", evidence=algo_str)
                                        break
                        except (ValueError, TypeError):
                            pass

            self.generic_visit(node)

    CryptoVisitor().visit(tree)
    return findings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scan_file(rel_path: str, content: bytes) -> list[RawFinding]:
    """
    Scan a single file's content for cryptographic usage.

    Args:
        rel_path: Path relative to the archive root (used as finding file_path)
        content: Raw bytes of the file

    Returns:
        List of RawFinding (may be empty)
    """
    ext = Path(rel_path).suffix.lower()
    rules = get_rules_for_extension(ext)

    try:
        text = content.decode("utf-8", errors="replace")
    except Exception:
        return []

    lines = text.splitlines()

    # Regex pass
    findings = _regex_scan_lines(lines, ext, rel_path, rules)

    # Python AST pass (upgrades/adds findings)
    if ext == ".py":
        ast_findings = _ast_scan(text, rel_path)
        # Build set of (lineno, algo) already seen via regex, avoid duplicates
        seen = {(f.line_number, f.algorithm) for f in findings}
        for af in ast_findings:
            key = (af.line_number, af.algorithm)
            if key not in seen:
                findings.append(af)
                seen.add(key)
            else:
                # Upgrade regex finding with AST confidence
                for f in findings:
                    if f.line_number == af.line_number and f.algorithm == af.algorithm:
                        f.confidence = max(f.confidence, af.confidence)
                        f.detection_method = "ast"
                        break

    # Deduplicate: same rule + same line → keep highest confidence
    deduped: dict[tuple, RawFinding] = {}
    for f in findings:
        key = (f.rule_id, f.file_path, f.line_number)
        if key not in deduped or f.confidence > deduped[key].confidence:
            deduped[key] = f

    return list(deduped.values())
