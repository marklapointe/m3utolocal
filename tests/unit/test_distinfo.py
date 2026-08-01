from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def test_distinfo_exists_and_well_formed():
    di = ROOT / "ports" / "net" / "m3utolocal" / "distinfo"
    assert di.is_file()
    text = di.read_text(encoding="utf-8")
    assert "SHA256 (m3utolocal-1.1.0.tar.gz)" in text
    assert "SIZE (m3utolocal-1.1.0.tar.gz)" in text
    assert "TIMESTAMP" in text


def test_release_tarball_matches_distinfo():
    import hashlib
    import re

    di = (ROOT / "ports" / "net" / "m3utolocal" / "distinfo").read_text(encoding="utf-8")
    sha_m = re.search(r"SHA256 \(m3utolocal-1\.1\.0\.tar\.gz\) = ([0-9a-f]+)", di)
    size_m = re.search(r"SIZE \(m3utolocal-1\.1\.0\.tar\.gz\) = (\d+)", di)
    assert sha_m and size_m
    tarball = ROOT / "dist" / "m3utolocal-1.1.0.tar.gz"
    assert tarball.is_file()
    data = tarball.read_bytes()
    assert str(len(data)) == size_m.group(1)
    assert hashlib.sha256(data).hexdigest() == sha_m.group(1)
