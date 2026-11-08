"""Tests for APK signatures and certificate fingerprints."""

from __future__ import annotations

import io
import zipfile
import pytest
from pureapk.cli import main
from pureapk.signature import APKCertificate, APKSigner, APKSignature


def test_apk_certificate_fingerprints() -> None:
    raw_cert = b"DUMMY_CERTIFICATE_CONTENT"
    cert = APKCertificate("META-INF/CERT.RSA", raw_cert)
    assert cert.filename == "META-INF/CERT.RSA"
    assert len(cert.sha256) == 64
    assert len(cert.sha1) == 40
    assert len(cert.md5) == 32

    d = cert.as_dict()
    assert d["filename"] == "META-INF/CERT.RSA"
    assert d["sha256"] == cert.sha256


def test_apk_signature_v1(sample_apk_bytes: bytes) -> None:
    zf = zipfile.ZipFile(io.BytesIO(sample_apk_bytes))
    sig = APKSignature.inspect(zf, sample_apk_bytes)
    assert sig.has_v1 is True
    assert sig.is_signed is True
    assert "v1" in sig.scheme_names
    assert len(sig.certificates) >= 1

    d = sig.as_dict()
    assert d["is_signed"] is True
    assert "v1" in d["schemes"]
    assert len(d["certificates"]) >= 1


def test_unsigned_apk() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("test.txt", b"hello")
    zf = zipfile.ZipFile(buf)
    sig = APKSignature.inspect(zf, buf.getvalue())
    assert sig.has_v1 is False
    assert sig.has_v2 is False
    assert sig.is_signed is False
    assert len(sig.scheme_names) == 0


def test_apk_signer_in_memory() -> None:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("AndroidManifest.xml", b"TEST_DATA")
        zf.writestr("classes.dex", b"DEX_DATA")

    unsigned_bytes = buf.getvalue()
    signed_bytes = APKSigner.sign_apk_bytes(unsigned_bytes)
    assert len(signed_bytes) > len(unsigned_bytes)

    signed_zf = zipfile.ZipFile(io.BytesIO(signed_bytes))
    sig = APKSignature.inspect(signed_zf, raw_bytes=signed_bytes)
    assert sig.is_signed is True
    assert sig.has_v1 is True
    assert sig.has_v2 is True
    assert "v1" in sig.scheme_names
    assert "v2" in sig.scheme_names
    assert len(sig.certificates) >= 1


def test_apk_signer_file(tmp_path: pytest.TempPathFactory) -> None:
    from pathlib import Path
    p = Path(str(tmp_path)) / "unsigned.apk"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("AndroidManifest.xml", b"DATA")
    
    out_p = Path(str(tmp_path)) / "signed.apk"
    APKSigner.sign_apk_file(p, output_path=out_p)
    assert out_p.exists()

    with zipfile.ZipFile(out_p) as zf:
        sig = APKSignature.inspect(zf, out_p.read_bytes())
        assert sig.is_signed is True
        assert sig.has_v1 is True
        assert sig.has_v2 is True


def test_cli_sign_command(tmp_path: pytest.TempPathFactory) -> None:
    from pathlib import Path
    in_apk = Path(str(tmp_path)) / "input.apk"
    with zipfile.ZipFile(in_apk, "w") as zf:
        zf.writestr("classes.dex", b"DEX")

    out_apk = Path(str(tmp_path)) / "cli_signed.apk"
    code = main(["sign", str(in_apk), "-o", str(out_apk)])
    assert code == 0
    assert out_apk.exists()

    with zipfile.ZipFile(out_apk) as zf:
        sig = APKSignature.inspect(zf, out_apk.read_bytes())
        assert sig.is_signed is True
        assert sig.has_v1 is True
        assert sig.has_v2 is True

