"""Tests for binding p4a ``private_version`` to the private.tar content."""

import hashlib
import zipfile

import pytest

from pureapk.frameworks import patch_arsc_private_version

OLD = b"0ebf6a2770bfa102cca304a06d01d3440f779647"


def _fake_arsc(value: bytes = OLD) -> bytes:
    return b"\x02\x00\x0c\x00HEADER" + b"\x07\x07#000000\x00" + b"\x28\x28" + value + b"\x00" + b"\x04\x04kivy\x00TAIL"


def test_patch_replaces_value_in_place() -> None:
    new = hashlib.sha1(b"tar").hexdigest()
    arsc = _fake_arsc()
    patched = patch_arsc_private_version(arsc, new)
    assert len(patched) == len(arsc)
    assert OLD not in patched
    assert new.encode() in patched
    assert patched.replace(new.encode(), OLD) == arsc


def test_patch_no_match_returns_input() -> None:
    arsc = b"no version here"
    assert patch_arsc_private_version(arsc, "a" * 40) is arsc


def test_patch_ambiguous_returns_input() -> None:
    arsc = _fake_arsc() + b"\x28\x28" + b"b" * 40 + b"\x00"
    assert patch_arsc_private_version(arsc, "c" * 40) == arsc


def test_patch_rejects_bad_version() -> None:
    with pytest.raises(ValueError):
        patch_arsc_private_version(_fake_arsc(), "xyz")


def test_pack_binds_private_version_to_private_tar(tmp_path) -> None:
    from pureapk.frameworks import KivyAppHelper

    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / "main.py").write_text("print('hi')\n", encoding="utf-8")
    (proj / "resources.arsc").write_bytes(_fake_arsc())
    out = tmp_path / "app.apk"
    KivyAppHelper.pack_app(proj, out)

    with zipfile.ZipFile(out) as z:
        tar = z.read("assets/private.tar")
        assert z.getinfo("assets/private.tar").compress_type == zipfile.ZIP_STORED
        arsc = z.read("resources.arsc")
    assert hashlib.sha1(tar).hexdigest().encode() in arsc
    assert OLD not in arsc
