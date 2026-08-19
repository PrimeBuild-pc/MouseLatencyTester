"""The updater downloads and runs an executable, so its guard rails are
tested directly: version comparison, host allow-listing, and above all that a
file whose checksum does not match is deleted and never returned.
"""

import hashlib
import io
import json
import urllib.error

import pytest

from latency_tester import updater
from latency_tester.updater import Release, UpdateError


# ------------------------------------------------------------- versions ----
@pytest.mark.parametrize("text, expected", [
    ("1.2.3", (1, 2, 3)),
    ("v1.2.3", (1, 2, 3)),
    ("v10.0.1", (10, 0, 1)),
    ("  v2.0.0  ", (2, 0, 0)),
    ("v1.2.3-beta", (1, 2, 3)),
])
def test_parse_version(text, expected):
    assert updater.parse_version(text) == expected


@pytest.mark.parametrize("text", ["", "latest", "vX.Y.Z", "1.2"])
def test_parse_version_rejects_junk(text):
    assert updater.parse_version(text) is None


@pytest.mark.parametrize("candidate, current, newer", [
    ("v1.0.1", "1.0.0", True),
    ("v1.1.0", "1.0.9", True),
    ("v2.0.0", "1.9.9", True),
    ("v1.0.0", "1.0.0", False),
    ("v0.9.9", "1.0.0", False),
    ("v1.0.0", "1.0.1", False),
    ("v10.0.0", "9.0.0", True),      # not string comparison
])
def test_is_newer(candidate, current, newer):
    assert updater.is_newer(candidate, current) is newer


def test_is_newer_is_false_when_either_side_is_unparseable():
    assert updater.is_newer("garbage", "1.0.0") is False
    assert updater.is_newer("v1.0.0", "garbage") is False


# ----------------------------------------------------------------- URLs ----
@pytest.mark.parametrize("url", [
    "http://github.com/x",                       # not https
    "https://evil.example.com/setup.exe",        # not a GitHub host
    "https://github.com.evil.com/setup.exe",     # look-alike host
    "ftp://github.com/setup.exe",
])
def test_untrusted_urls_are_refused(url):
    with pytest.raises(UpdateError):
        updater._check_url(url)


@pytest.mark.parametrize("url", [
    "https://api.github.com/repos/x/y/releases/latest",
    "https://github.com/o/r/releases/download/v1/setup.exe",
    "https://objects.githubusercontent.com/blah",
])
def test_github_urls_are_accepted(url):
    assert updater._check_url(url) == url


def test_the_repository_is_hard_coded():
    """Nothing configurable may redirect the updater elsewhere."""
    assert updater.REPO == "PrimeBuild-pc/MouseLatencyTester"
    assert updater.API_LATEST.startswith("https://api.github.com/repos/")
    assert updater.REPO in updater.API_LATEST


# -------------------------------------------------------------- check ------
def fake_api(monkeypatch, payload):
    def urlopen(request, *args, **kwargs):
        body = json.dumps(payload).encode()
        return io.BytesIO(body)
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)


def release_payload(tag="v2.0.0", assets=True):
    payload = {"tag_name": tag, "body": "notes", "html_url": "https://github.com/x/y/releases/v2",
               "assets": []}
    if assets:
        payload["assets"] = [
            {"name": "LatencyTester-2.0.0-Setup.exe", "size": 1234,
             "browser_download_url": "https://github.com/o/r/releases/download/v2/s.exe"},
            {"name": "SHA256SUMS.txt", "size": 90,
             "browser_download_url": "https://github.com/o/r/releases/download/v2/SHA256SUMS.txt"},
        ]
    return payload


def test_check_reports_a_newer_release(monkeypatch):
    fake_api(monkeypatch, release_payload())
    release = updater.check_for_update(current="1.0.0")
    assert release is not None
    assert release.version == "2.0.0"
    assert release.asset_name.endswith(".exe")
    assert release.checksums_url is not None


def test_check_returns_none_when_current(monkeypatch):
    fake_api(monkeypatch, release_payload(tag="v1.0.0"))
    assert updater.check_for_update(current="1.0.0") is None


def test_check_returns_none_when_ahead(monkeypatch):
    fake_api(monkeypatch, release_payload(tag="v1.0.0"))
    assert updater.check_for_update(current="1.5.0") is None


def test_check_rejects_a_release_without_an_installer(monkeypatch):
    fake_api(monkeypatch, release_payload(assets=False))
    with pytest.raises(UpdateError, match="no installer"):
        updater.check_for_update(current="1.0.0")


def test_check_rejects_an_unparseable_tag(monkeypatch):
    fake_api(monkeypatch, release_payload(tag="latest"))
    with pytest.raises(UpdateError, match="unrecognised"):
        updater.check_for_update(current="1.0.0")


def test_network_failure_becomes_a_readable_error(monkeypatch):
    def urlopen(*args, **kwargs):
        raise urllib.error.URLError("no route to host")
    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    with pytest.raises(UpdateError, match="could not reach GitHub"):
        updater.check_for_update(current="1.0.0")


# ----------------------------------------------------------- download ------
PAYLOAD = b"pretend installer bytes"
DIGEST = hashlib.sha256(PAYLOAD).hexdigest()


def make_release(**overrides):
    defaults = dict(
        version="2.0.0", tag="v2.0.0", notes="",
        asset_name="LatencyTester-2.0.0-Setup.exe",
        asset_url="https://github.com/o/r/releases/download/v2/s.exe",
        asset_size=len(PAYLOAD),
        checksums_url="https://github.com/o/r/releases/download/v2/SHA256SUMS.txt",
        page_url="https://github.com/o/r/releases/v2",
    )
    defaults.update(overrides)
    return Release(**defaults)


class FakeResponse(io.BytesIO):
    """BytesIO plus the ``headers`` a real urlopen response carries."""

    def __init__(self, data: bytes):
        super().__init__(data)
        self.headers = {"Content-Length": str(len(data))}

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
        return False


def fake_download(monkeypatch, body=PAYLOAD, checksum_line=None):
    if checksum_line is None:
        checksum_line = f"{DIGEST}  LatencyTester-2.0.0-Setup.exe"

    def _open(url):
        if "SHA256SUMS" in url:
            return FakeResponse(checksum_line.encode())
        return FakeResponse(body)

    monkeypatch.setattr(updater, "_open", _open)


def test_download_verifies_the_checksum(monkeypatch, tmp_path):
    fake_download(monkeypatch)
    path = updater.download(make_release(), destination=tmp_path)
    assert path.read_bytes() == PAYLOAD


def test_a_tampered_download_is_deleted_and_raises(monkeypatch, tmp_path):
    """The single most important guarantee in this module."""
    fake_download(monkeypatch, body=b"malicious payload")
    with pytest.raises(UpdateError, match="does not match"):
        updater.download(make_release(), destination=tmp_path)
    assert list(tmp_path.iterdir()) == []          # nothing left behind


def test_a_release_without_a_checksum_line_is_refused(monkeypatch, tmp_path):
    fake_download(monkeypatch, checksum_line="deadbeef  some-other-file.exe")
    with pytest.raises(UpdateError, match="does not publish a checksum"):
        updater.download(make_release(), destination=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_a_release_with_no_checksums_asset_is_refused(monkeypatch, tmp_path):
    fake_download(monkeypatch)
    with pytest.raises(UpdateError, match="no SHA256SUMS"):
        updater.download(make_release(checksums_url=None), destination=tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_an_implausibly_large_asset_is_refused(tmp_path):
    with pytest.raises(UpdateError, match="implausibly large"):
        updater.download(make_release(asset_size=updater.MAX_DOWNLOAD_BYTES + 1),
                         destination=tmp_path)


def test_a_malicious_asset_name_cannot_escape_the_directory(monkeypatch, tmp_path):
    fake_download(monkeypatch,
                  checksum_line=f"{DIGEST}  ../../evil.exe")
    release = make_release(asset_name="../../evil.exe")
    # It either refuses or writes strictly inside tmp_path -- never outside.
    try:
        path = updater.download(release, destination=tmp_path)
    except UpdateError:
        pass
    else:
        assert tmp_path in path.parents


def test_progress_is_reported(monkeypatch, tmp_path):
    fake_download(monkeypatch)
    seen = []
    updater.download(make_release(), progress=lambda d, t: seen.append(d),
                     destination=tmp_path)
    assert seen and seen[-1] == len(PAYLOAD)


def test_size_mb_is_human_readable():
    assert make_release(asset_size=29 * 1024 * 1024).size_mb == 29.0
