"""Tests for APK signatures and certificate fingerprints."""

from __future__ import annotations

import io
import zipfile
import pytest
from pureapk.signature import APKCertificate, APKSignature


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
