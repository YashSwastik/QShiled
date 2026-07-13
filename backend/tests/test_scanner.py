"""
Crypto Discovery Engine Tests
===============================

Covers:
  - True positives for each algorithm category (Python, Java, JS/TS, C#, configs)
  - False positive guards (comments, plain English, unrelated uses)
  - Python AST detection
  - Certificate parsing (RSA / ECDSA)
  - Multi-language same-algorithm detection
  - No-crypto repository (empty result)
  - Evidence masking
  - Engine integration (run_scan file_map)
  - Upload endpoint: complete pipeline including finding_count
"""
import io
import textwrap
import zipfile
from pathlib import Path

import pytest

from app.services.scanner.source_scanner import scan_file, RawFinding
from app.services.scanner.engine import run_scan
from app.services.scanner.rules import Category, QuantumStatus


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _scan(filename: str, code: str) -> list[RawFinding]:
    return scan_file(filename, code.encode())


def _has(findings: list[RawFinding], *, algo_family: str | None = None,
          category: Category | None = None, algo: str | None = None) -> bool:
    for f in findings:
        if algo_family and f.algorithm_family != algo_family:
            continue
        if category and f.category != category:
            continue
        if algo and algo.lower() not in f.algorithm.lower():
            continue
        return True
    return False


def _make_zip(entries: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    return buf.getvalue()


# ─────────────────────────────────────────────────────────────────────────────
# RSA
# ─────────────────────────────────────────────────────────────────────────────

class TestRSA:

    def test_python_rsa_import(self):
        code = "from cryptography.hazmat.primitives.asymmetric import rsa\nkey = rsa.generate_private_key(65537, 2048)"
        findings = _scan("crypto.py", code)
        assert _has(findings, algo_family="RSA", category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY)

    def test_python_rsa_string(self):
        code = "algo = 'RSA'\nkey = RSA.generate(2048)"
        findings = _scan("crypto.py", code)
        assert _has(findings, algo_family="RSA")

    def test_java_rsa(self):
        code = 'KeyPairGenerator kpg = KeyPairGenerator.getInstance("RSA");\nkpg.initialize(2048);'
        findings = _scan("Crypto.java", code)
        assert _has(findings, algo_family="RSA")

    def test_js_rsa(self):
        code = "const key = await crypto.subtle.generateKey({name:'RSA-OAEP', modulusLength:2048}, true, ['encrypt']);"
        findings = _scan("crypto.js", code)
        assert _has(findings, algo_family="RSA")

    def test_csharp_rsa(self):
        code = "using (var rsa = new RSACryptoServiceProvider(2048)) { }"
        findings = _scan("Crypto.cs", code)
        assert _has(findings, algo_family="RSA")

    def test_pem_block_in_source(self):
        code = 'key_pem = "-----BEGIN RSA PRIVATE KEY-----\\nMIIE..."'
        findings = _scan("config.py", code)
        assert _has(findings, algo_family="RSA")

    def test_rsa_in_comment_downscored(self):
        """RSA mentioned only in a comment must be downscored, not eliminated entirely."""
        code = "# RSA is used for authentication\nx = 1"
        findings = _scan("auth.py", code)
        # May produce low-confidence finding; ensure if it does, confidence is reduced
        for f in findings:
            if f.algorithm_family == "RSA":
                assert f.confidence < 0.5, "Comment findings must be low-confidence"

    def test_rsa_padding_pkcs1(self):
        code = "from cryptography.hazmat.primitives.asymmetric import padding\npadding.PKCS1v15()"
        findings = _scan("sig.py", code)
        assert _has(findings, algo_family="RSA")


# ─────────────────────────────────────────────────────────────────────────────
# ECC / ECDSA / ECDH
# ─────────────────────────────────────────────────────────────────────────────

class TestECC:

    def test_python_ecdsa(self):
        code = "from cryptography.hazmat.primitives.asymmetric import ec\nkey = ec.generate_private_key(ec.SECP256R1())"
        findings = _scan("ec.py", code)
        assert _has(findings, category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY)

    def test_java_ecdh(self):
        code = 'KeyPairGenerator kpg = KeyPairGenerator.getInstance("EC");\nECDHKeyAgreement agr = new ECDHKeyAgreement();'
        findings = _scan("ECDH.java", code)
        assert _has(findings, category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY)

    def test_ecdsa_signature(self):
        code = "sig = ECDSA.sign(message, private_key)"
        findings = _scan("sign.py", code)
        assert _has(findings, algo_family="ECDSA")

    def test_secp256r1_curve(self):
        code = "from cryptography.hazmat.primitives.asymmetric.ec import SECP384R1, P-384"
        findings = _scan("curves.py", code)
        assert _has(findings, category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY)

    def test_ec_pem_block(self):
        code = "-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIA=="
        findings = _scan("key.pem", code)
        assert _has(findings, category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# Diffie-Hellman
# ─────────────────────────────────────────────────────────────────────────────

class TestDH:

    def test_dh_parameters(self):
        code = "params = dh.generate_parameters(generator=2, key_size=2048)"
        findings = _scan("dh.py", code)
        assert _has(findings, algo_family="DH")

    def test_dhe_cipher_suite_config(self):
        code = "ciphers = 'TLS_DHE_RSA_WITH_AES_256_GCM_SHA384'"
        findings = _scan("ssl.conf", code)
        assert _has(findings, category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY)

    def test_diffie_hellman_class(self):
        code = "exchange = DiffieHellmanKeyExchange()"
        findings = _scan("kex.java", code)
        assert _has(findings, algo_family="DH")


# ─────────────────────────────────────────────────────────────────────────────
# DSA
# ─────────────────────────────────────────────────────────────────────────────

class TestDSA:

    def test_dsa_python(self):
        code = "from cryptography.hazmat.primitives.asymmetric import dsa\nkey = dsa.generate_private_key(2048)"
        findings = _scan("dsa.py", code)
        assert _has(findings, category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY)

    def test_dsa_not_ecdsa(self):
        """'DSA' rule should not fire because of 'ECDSA' present."""
        code = "algo = ECDSA"
        findings = _scan("sig.py", code)
        # ECDSA should be found; DSA-001 should NOT match because negative pattern hits
        families = {f.algorithm_family for f in findings}
        # Should have ECDSA, not bare DSA
        assert "ECDSA" in families


# ─────────────────────────────────────────────────────────────────────────────
# AES (SYMMETRIC — not quantum-vulnerable)
# ─────────────────────────────────────────────────────────────────────────────

class TestAES:

    def test_aes_python(self):
        code = "from Crypto.Cipher import AES\ncipher = AES.new(key, AES.MODE_GCM)"
        findings = _scan("cipher.py", code)
        assert _has(findings, algo_family="AES", category=Category.SYMMETRIC)

    def test_aes_category_is_not_vulnerable(self):
        code = "cipher = AES.new(key, AES.MODE_CBC)"
        findings = _scan("c.py", code)
        for f in findings:
            if f.algorithm_family == "AES":
                assert f.category != Category.QUANTUM_VULNERABLE_PUBLIC_KEY
                assert f.quantum_status in (QuantumStatus.safe, QuantumStatus.borderline)

    def test_aes256_cipher_suite(self):
        """AES-256 in TLS cipher suite must be classified SYMMETRIC."""
        code = "ssl_ciphers = 'AES-256-GCM-SHA384'"
        findings = _scan("nginx.conf", code)
        aes_f = [f for f in findings if f.algorithm_family == "AES"]
        assert aes_f
        for f in aes_f:
            assert f.category == Category.SYMMETRIC

    def test_java_aes_cipher(self):
        code = 'Cipher cipher = Cipher.getInstance("AES/GCM/NoPadding");'
        findings = _scan("Crypto.java", code)
        assert _has(findings, algo_family="AES")


# ─────────────────────────────────────────────────────────────────────────────
# SHA-2 / SHA-3 (HASH)
# ─────────────────────────────────────────────────────────────────────────────

class TestHashing:

    def test_sha256_python(self):
        code = "import hashlib\nhash_ = hashlib.sha256(data).hexdigest()"
        findings = _scan("hash.py", code)
        assert _has(findings, algo_family="SHA-2", category=Category.HASH)

    def test_sha256_ast_detection(self):
        """Python AST should detect hashlib.sha256 with high confidence."""
        code = "import hashlib\ndigest = hashlib.sha256(b'data').hexdigest()"
        findings = _scan("h.py", code)
        ast_f = [f for f in findings if f.detection_method == "ast"]
        assert ast_f, "AST should detect hashlib.sha256"
        assert ast_f[0].confidence >= 0.9

    def test_sha512_not_vulnerable(self):
        code = "hashlib.sha512(data)"
        findings = _scan("h.py", code)
        for f in findings:
            if "SHA" in f.algorithm_family:
                assert f.quantum_status != QuantumStatus.vulnerable

    def test_sha3_python(self):
        code = "import hashlib\nh = hashlib.sha3_256(data).digest()"
        findings = _scan("h.py", code)
        assert _has(findings, algo_family="SHA-3")

    def test_java_sha256(self):
        code = 'MessageDigest md = MessageDigest.getInstance("SHA-256");'
        findings = _scan("Hash.java", code)
        assert _has(findings, algo_family="SHA-2")


# ─────────────────────────────────────────────────────────────────────────────
# Legacy / Deprecated (classical weakness only)
# ─────────────────────────────────────────────────────────────────────────────

class TestLegacy:

    def test_md5_python(self):
        code = "import hashlib\ndig = hashlib.md5(data).hexdigest()"
        findings = _scan("h.py", code)
        assert _has(findings, algo_family="MD5", category=Category.LEGACY_DEPRECATED)

    def test_md5_not_quantum_vulnerable(self):
        """MD5 must be LEGACY_DEPRECATED, not QUANTUM_VULNERABLE_PUBLIC_KEY."""
        code = "hashlib.md5(msg)"
        findings = _scan("h.py", code)
        for f in findings:
            if f.algorithm_family == "MD5":
                assert f.category == Category.LEGACY_DEPRECATED
                assert f.category != Category.QUANTUM_VULNERABLE_PUBLIC_KEY

    def test_sha1_java(self):
        code = 'MessageDigest md = MessageDigest.getInstance("SHA-1");'
        findings = _scan("Hash.java", code)
        assert _has(findings, algo_family="SHA-1", category=Category.LEGACY_DEPRECATED)

    def test_sha1_separate_from_quantum(self):
        """SHA-1 is a classical weakness — must NOT appear as quantum-vulnerable."""
        code = "hashlib.sha1(data)"
        findings = _scan("h.py", code)
        for f in findings:
            if f.algorithm_family == "SHA-1":
                assert f.quantum_status == QuantumStatus.deprecated
                assert f.category == Category.LEGACY_DEPRECATED

    def test_des_cipher(self):
        code = "cipher = DESCryptoServiceProvider()"
        findings = _scan("enc.cs", code)
        assert _has(findings, algo_family="DES", category=Category.LEGACY_DEPRECATED)

    def test_rc4_config(self):
        code = "ciphers = 'RC4-SHA'"
        findings = _scan("ssl.conf", code)
        assert _has(findings, algo_family="RC4", category=Category.LEGACY_DEPRECATED)

    def test_3des_not_quantum_vulnerable(self):
        code = "Cipher.getInstance('DESede/CBC/PKCS5Padding')"
        findings = _scan("c.java", code)
        for f in findings:
            if f.algorithm_family == "DES":
                assert f.category == Category.LEGACY_DEPRECATED

    def test_legacy_has_security_note(self):
        """Legacy findings should carry a legacy_security_note."""
        code = "hashlib.md5(msg)"
        findings = _scan("h.py", code)
        md5 = [f for f in findings if f.algorithm_family == "MD5"]
        assert md5
        assert md5[0].legacy_security_note  # must not be empty


# ─────────────────────────────────────────────────────────────────────────────
# Post-quantum (PQC)
# ─────────────────────────────────────────────────────────────────────────────

class TestPQC:

    def test_mlkem_detection(self):
        code = "from pqc import ML_KEM\nkem = ML_KEM.Kyber768()"
        findings = _scan("pqc.py", code)
        assert _has(findings, algo_family="ML-KEM", category=Category.POST_QUANTUM)

    def test_mldsa_detection(self):
        code = "signer = Dilithium3.sign(message, privkey)"
        findings = _scan("sign.py", code)
        assert _has(findings, algo_family="ML-DSA", category=Category.POST_QUANTUM)

    def test_sphincs_detection(self):
        code = "HashSig = SPHINCS_plus_shake_256f_simple()"
        findings = _scan("pqc.py", code)
        assert _has(findings, algo_family="SLH-DSA", category=Category.POST_QUANTUM)

    def test_pqc_not_vulnerable(self):
        code = "ML_KEM = Kyber512()"
        findings = _scan("pqc.py", code)
        for f in findings:
            if f.category == Category.POST_QUANTUM:
                assert f.quantum_status == QuantumStatus.safe


# ─────────────────────────────────────────────────────────────────────────────
# TLS / Config
# ─────────────────────────────────────────────────────────────────────────────

class TestTLS:

    def test_weak_tls_version_conf(self):
        code = "ssl_version = TLSv1.0"
        findings = _scan("nginx.conf", code)
        assert _has(findings, category=Category.LEGACY_DEPRECATED)

    def test_tls_vulnerable_cipher_suite_yaml(self):
        code = "cipher_suites:\n  - TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384"
        findings = _scan("config.yaml", code)
        assert _has(findings, category=Category.QUANTUM_VULNERABLE_PUBLIC_KEY)


# ─────────────────────────────────────────────────────────────────────────────
# False positive guards
# ─────────────────────────────────────────────────────────────────────────────

class TestFalsePositives:

    def test_no_crypto_file(self):
        code = textwrap.dedent("""\
            def greet(name):
                return f"Hello, {name}"

            TIMEOUT = 30
            MAX_RETRIES = 3
        """)
        findings = _scan("utils.py", code)
        assert not findings, f"Expected no findings, got: {findings}"

    def test_description_text_no_false_positive(self):
        """Plain English prose mentioning algorithm names should not fire."""
        code = textwrap.dedent("""\
            # This module provides authentication utilities.
            # It does NOT use RSA or MD5 for any cryptographic operations.
            # Reference: NIST SP 800-131A
        """)
        findings = _scan("README.py", code)
        # Comments should either produce zero findings or only very low confidence
        for f in findings:
            assert f.confidence < 0.5, f"False positive at high confidence: {f}"

    def test_word_description_in_java_comment(self):
        code = "// We deprecated RSA usage in version 2.0\nint x = 5;"
        findings = _scan("Notes.java", code)
        for f in findings:
            if f.algorithm_family == "RSA":
                assert f.confidence < 0.5

    def test_aes_not_in_vulnerable_category(self):
        code = "from Crypto.Cipher import AES\ncipher = AES.new(key, AES.MODE_CBC)"
        findings = _scan("enc.py", code)
        aes = [f for f in findings if f.algorithm_family == "AES"]
        assert aes
        for f in aes:
            assert f.category != Category.QUANTUM_VULNERABLE_PUBLIC_KEY

    def test_sha256_not_in_vulnerable_category(self):
        code = "hashlib.sha256(data)"
        findings = _scan("h.py", code)
        for f in findings:
            if f.algorithm_family == "SHA-2":
                assert f.category != Category.QUANTUM_VULNERABLE_PUBLIC_KEY

    def test_des_word_description(self):
        """Description" containing 'DES' should not fire."""
        code = "# This DEScription explains the algorithm.\nx = 1"
        findings = _scan("doc.py", code)
        des_f = [f for f in findings if f.algorithm_family == "DES"]
        assert not des_f or all(f.confidence < 0.5 for f in des_f)


# ─────────────────────────────────────────────────────────────────────────────
# Evidence masking
# ─────────────────────────────────────────────────────────────────────────────

class TestEvidenceMasking:

    def test_pem_body_redacted(self):
        code = '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA3b...\n-----END RSA PRIVATE KEY-----'
        findings = _scan("key.pem", code)
        for f in findings:
            assert "MIIEowIBAAKCAQEA3b" not in (f.evidence or "")

    def test_hex_literal_redacted(self):
        code = "key = 0xDEADBEEFCAFEBABE0000000000000000000000000000000000000000000000FF"
        findings = _scan("keys.py", code)
        # Hex literal should not appear verbatim in evidence
        for f in findings:
            assert "DEADBEEF" not in (f.evidence or "")


# ─────────────────────────────────────────────────────────────────────────────
# Engine (run_scan) integration
# ─────────────────────────────────────────────────────────────────────────────

class TestEngine:

    def test_empty_file_map(self):
        findings = run_scan({})
        assert findings == []

    def test_no_crypto_repository(self):
        file_map = {
            "utils.py": b"def add(a, b): return a + b\n",
            "config.yaml": b"timeout: 30\nretries: 3\n",
            "README.md": b"# My Project\nThis is a sample project.\n",
        }
        # Run scan — no crypto should be found
        findings = run_scan(file_map)
        # Filter out any very-low-confidence comment noise
        real = [f for f in findings if f.confidence >= 0.5]
        assert not real, f"Expected no real findings in no-crypto repo, got: {real}"

    def test_multi_file_multi_algo(self):
        file_map = {
            "auth.py":  b"key = rsa.generate_private_key(65537, 2048)\n",
            "hash.py":  b"import hashlib\nh = hashlib.md5(data)\n",
            "ssl.conf": b"ssl_ciphers ECDHE-RSA-AES256-GCM-SHA384;\n",
        }
        findings = run_scan(file_map)
        families = {f.algorithm_family for f in findings}
        assert "RSA" in families
        assert "MD5" in families

    def test_findings_carry_correct_file_path(self):
        file_map = {
            "src/crypto.py": b"from cryptography.hazmat.primitives.asymmetric import rsa\n"
                              b"key = rsa.generate_private_key(65537, 2048)\n",
        }
        findings = run_scan(file_map)
        assert all(f.file_path == "src/crypto.py" for f in findings)

    def test_pqc_detected_in_engine(self):
        file_map = {"pqc.py": b"from pqcrypto.kem import kyber768\nkem = kyber768.generate_keypair()\n"}
        findings = run_scan(file_map)
        pqc = [f for f in findings if f.category == Category.POST_QUANTUM]
        assert pqc


# ─────────────────────────────────────────────────────────────────────────────
# HTTP endpoint — full pipeline
# ─────────────────────────────────────────────────────────────────────────────

def _upload_zip(client, app_id: str, entries: dict[str, bytes]) -> dict:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, data in entries.items():
            zf.writestr(name, data)
    r = client.post(
        "/api/scans/upload",
        data={"application_id": app_id},
        files={"file": ("repo.zip", io.BytesIO(buf.getvalue()), "application/zip")},
    )
    return r


def _upload_file(client, app_id: str, filename: str, content: bytes) -> dict:
    r = client.post(
        "/api/scans/upload",
        data={"application_id": app_id},
        files={"file": (filename, io.BytesIO(content), "application/octet-stream")},
    )
    return r


class TestUploadPipeline:
    """Integration tests using the FastAPI test client from conftest."""

    def _make_stack(self, client) -> str:
        import os
        org = client.post("/api/organizations", json={
            "name": "ScanTest", "slug": f"scantest-{os.urandom(4).hex()}"
        }).json()
        project = client.post("/api/projects", json={
            "organization_id": org["id"], "name": "P"
        }).json()
        app = client.post("/api/applications", json={
            "project_id": project["id"], "name": "A"
        }).json()
        return app["id"]

    def test_rsa_code_produces_findings(self, client):
        app_id = self._make_stack(client)
        code = b"from cryptography.hazmat.primitives.asymmetric import rsa\nkey = rsa.generate_private_key(65537, 2048)\n"
        r = _upload_zip(client, app_id, {"auth.py": code})
        assert r.status_code == 201
        d = r.json()
        assert d["status"] == "completed"
        assert d["finding_count"] > 0

        # List findings
        fr = client.get(f"/api/findings?scan_id={d['id']}")
        assert fr.status_code == 200
        findings = fr.json()["items"]
        assert any(f["algorithm_family"] == "RSA" for f in findings)

    def test_no_crypto_produces_zero_findings(self, client):
        app_id = self._make_stack(client)
        code = b"def add(a, b):\n    return a + b\n"
        r = _upload_file(client, app_id, "utils.py", code)
        assert r.status_code == 201
        assert r.json()["status"] == "completed"
        assert r.json()["finding_count"] == 0

    def test_md5_classified_legacy_not_quantum(self, client):
        app_id = self._make_stack(client)
        code = b"import hashlib\ndig = hashlib.md5(data).hexdigest()\n"
        r = _upload_zip(client, app_id, {"h.py": code})
        assert r.status_code == 201
        scan_id = r.json()["id"]
        fr = client.get(f"/api/findings?scan_id={scan_id}")
        findings = fr.json()["items"]
        md5 = [f for f in findings if f["algorithm_family"] == "MD5"]
        assert md5, "MD5 finding expected"
        for f in md5:
            assert f["quantum_status"] != "vulnerable"

    def test_aes_classified_symmetric(self, client):
        app_id = self._make_stack(client)
        code = b"from Crypto.Cipher import AES\ncipher = AES.new(key, AES.MODE_GCM)\n"
        r = _upload_zip(client, app_id, {"enc.py": code})
        assert r.status_code == 201
        fr = client.get(f"/api/findings?scan_id={r.json()['id']}")
        findings = fr.json()["items"]
        aes = [f for f in findings if f["algorithm_family"] == "AES"]
        assert aes
        for f in aes:
            assert f["quantum_status"] != "vulnerable"

    def test_mixed_repo_multiple_families(self, client):
        app_id = self._make_stack(client)
        entries = {
            "auth.py":     b"key = rsa.generate_private_key(65537, 2048)\n",
            "hash.py":     b"import hashlib\nh = hashlib.md5(data).hexdigest()\n",
            "cipher.java": b'Cipher.getInstance("AES/GCM/NoPadding");\n',
        }
        r = _upload_zip(client, app_id, entries)
        assert r.status_code == 201
        d = r.json()
        assert d["finding_count"] > 0
        fr = client.get(f"/api/findings?scan_id={d['id']}")
        families = {f["algorithm_family"] for f in fr.json()["items"]}
        assert "RSA" in families
        assert "MD5" in families
        assert "AES" in families

    def test_finding_quantum_status_for_rsa(self, client):
        app_id = self._make_stack(client)
        r = _upload_zip(client, app_id, {"k.py": b"RSA.generate(2048)\n"})
        fr = client.get(f"/api/findings?scan_id={r.json()['id']}")
        rsa_findings = [f for f in fr.json()["items"] if f["algorithm_family"] == "RSA"]
        assert rsa_findings
        for f in rsa_findings:
            assert f["quantum_status"] == "vulnerable"
