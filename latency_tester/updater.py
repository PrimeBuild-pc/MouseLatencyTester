"""One-click update from the project's GitHub releases.

Deliberately conservative, because this is the one feature that downloads and
runs an executable:

* the repository is **hard-coded** -- there is no setting or file that can
  redirect the updater somewhere else;
* only ``https://api.github.com`` and ``https://*.githubusercontent.com`` /
  ``https://github.com`` release URLs are accepted;
* the installer is verified against the ``SHA256SUMS.txt`` published with the
  same release before it is ever executed, and a mismatch aborts;
* nothing is downloaded or launched without the user saying yes.

No third-party dependency: ``urllib`` and ``hashlib`` are enough.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import ssl
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from . import __version__

log = logging.getLogger(__name__)

#: Hard-coded. Never read this from settings or from a downloaded file.
REPO = "PrimeBuild-pc/MouseLatencyTester"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
RELEASES_PAGE = f"https://github.com/{REPO}/releases/latest"

ALLOWED_HOSTS = {
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
    "raw.githubusercontent.com",
}

USER_AGENT = f"LatencyTester/{__version__}"
TIMEOUT_S = 20
CHECKSUM_ASSET = "SHA256SUMS.txt"
#: Refuse anything implausible for this installer (currently ~29 MB).
MAX_DOWNLOAD_BYTES = 300 * 1024 * 1024

VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


class UpdateError(Exception):
    """Anything that stops an update, phrased for a human."""


@dataclass(frozen=True)
class Release:
    version: str            # normalised, e.g. "1.2.0"
    tag: str                # as published, e.g. "v1.2.0"
    notes: str
    asset_name: str
    asset_url: str
    asset_size: int
    checksums_url: str | None
    page_url: str

    @property
    def size_mb(self) -> float:
        return round(self.asset_size / (1024 * 1024), 1)


def parse_version(text: str) -> tuple[int, int, int] | None:
    """``"v1.2.3"`` -> ``(1, 2, 3)``. Returns ``None`` if unparseable."""
    match = VERSION_RE.match(text.strip())
    return tuple(int(g) for g in match.groups()) if match else None  # type: ignore[return-value]


def is_newer(candidate: str, current: str = __version__) -> bool:
    """True when ``candidate`` is a strictly newer semantic version."""
    new, old = parse_version(candidate), parse_version(current)
    if new is None or old is None:
        return False
    return new > old


def _check_url(url: str) -> str:
    """Reject anything that is not an https URL on a GitHub host."""
    parts = urlparse(url)
    if parts.scheme != "https":
        raise UpdateError(f"refusing a non-HTTPS URL: {url}")
    if parts.hostname not in ALLOWED_HOSTS:
        raise UpdateError(f"refusing an unexpected host: {parts.hostname}")
    return url


def _open(url: str):
    request = urllib.request.Request(
        _check_url(url),
        headers={"User-Agent": USER_AGENT, "Accept": "application/octet-stream"},
    )
    context = ssl.create_default_context()
    return urllib.request.urlopen(request, timeout=TIMEOUT_S, context=context)


def check_for_update(current: str = __version__) -> Release | None:
    """Ask GitHub for the latest release.

    Returns ``None`` when already up to date. Raises :class:`UpdateError` with
    a readable message on any network or format problem.
    """
    request = urllib.request.Request(
        _check_url(API_LATEST),
        headers={"User-Agent": USER_AGENT,
                 "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_S,
                                    context=ssl.create_default_context()) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise UpdateError("no published release was found") from exc
        raise UpdateError(f"GitHub returned HTTP {exc.code}") from exc
    except urllib.error.URLError as exc:
        raise UpdateError(f"could not reach GitHub: {exc.reason}") from exc
    except (ValueError, TimeoutError) as exc:
        raise UpdateError(f"unexpected response from GitHub: {exc}") from exc

    tag = str(payload.get("tag_name") or "")
    if not parse_version(tag):
        raise UpdateError(f"unrecognised release tag: {tag!r}")
    if not is_newer(tag, current):
        return None

    installer = checksums = None
    for asset in payload.get("assets") or []:
        name = str(asset.get("name") or "")
        if name.lower().endswith(".exe"):
            installer = asset
        elif name == CHECKSUM_ASSET:
            checksums = asset
    if installer is None:
        raise UpdateError("the release has no installer attached")

    version = ".".join(str(n) for n in parse_version(tag))  # type: ignore[arg-type]
    return Release(
        version=version,
        tag=tag,
        notes=str(payload.get("body") or "").strip(),
        asset_name=str(installer["name"]),
        asset_url=str(installer["browser_download_url"]),
        asset_size=int(installer.get("size") or 0),
        checksums_url=str(checksums["browser_download_url"]) if checksums else None,
        page_url=str(payload.get("html_url") or RELEASES_PAGE),
    )


def _expected_digest(checksums_url: str, asset_name: str) -> str | None:
    """Pull the ``<sha256>  <filename>`` line for our asset."""
    try:
        with _open(checksums_url) as response:
            text = response.read(64 * 1024).decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, UpdateError) as exc:
        log.warning("could not fetch checksums: %s", exc)
        return None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[-1] == asset_name:
            digest = parts[0].strip().lower()
            if re.fullmatch(r"[0-9a-f]{64}", digest):
                return digest
    return None


def download(release: Release,
             progress: Callable[[int, int], None] | None = None,
             destination: Path | None = None) -> Path:
    """Download the installer and verify it. Returns the local path.

    ``progress`` receives ``(bytes_done, bytes_total)``. Raises
    :class:`UpdateError` if the download fails or the checksum does not match,
    and removes the partial file in that case.
    """
    if release.asset_size and release.asset_size > MAX_DOWNLOAD_BYTES:
        raise UpdateError("the published installer is implausibly large")

    target_dir = destination or Path(tempfile.mkdtemp(prefix="latency-tester-update-"))
    target_dir.mkdir(parents=True, exist_ok=True)
    # Never trust a server-supplied filename as a path.
    target = target_dir / Path(release.asset_name).name

    digest = hashlib.sha256()
    done = 0
    try:
        with _open(release.asset_url) as response, target.open("wb") as handle:
            total = int(response.headers.get("Content-Length") or release.asset_size or 0)
            while True:
                chunk = response.read(256 * 1024)
                if not chunk:
                    break
                done += len(chunk)
                if done > MAX_DOWNLOAD_BYTES:
                    raise UpdateError("the download exceeded the size limit")
                handle.write(chunk)
                digest.update(chunk)
                if progress:
                    progress(done, total)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        target.unlink(missing_ok=True)
        raise UpdateError(f"the download failed: {exc}") from exc
    except UpdateError:
        target.unlink(missing_ok=True)
        raise

    if release.checksums_url:
        expected = _expected_digest(release.checksums_url, release.asset_name)
        if expected is None:
            target.unlink(missing_ok=True)
            raise UpdateError(
                "the release does not publish a checksum for this file; "
                "the update was cancelled")
        actual = digest.hexdigest()
        if actual != expected:
            target.unlink(missing_ok=True)
            raise UpdateError(
                "the downloaded file does not match the published SHA-256 and "
                "was deleted. Do not install it.")
    else:
        target.unlink(missing_ok=True)
        raise UpdateError(
            f"the release publishes no {CHECKSUM_ASSET}; the update was "
            "cancelled because the download could not be verified")

    return target


def launch_installer(path: Path) -> None:
    """Start the verified installer and leave it to take over.

    The app is expected to close immediately afterwards so the installer can
    replace its files.
    """
    if sys.platform != "win32":
        raise UpdateError("automatic installation is only supported on Windows")
    if not path.is_file():
        raise UpdateError("the downloaded installer is missing")
    try:
        # /SILENT keeps the progress window but skips the wizard pages; the
        # user already agreed in the app.
        subprocess.Popen(
            [str(path), "/SILENT", "/NORESTART"],
            close_fds=True,
            creationflags=getattr(subprocess, "DETACHED_PROCESS", 0),
        )
    except OSError as exc:
        raise UpdateError(f"the installer could not be started: {exc}") from exc


def running_frozen() -> bool:
    """True when running from the packaged build rather than from source."""
    return bool(getattr(sys, "frozen", False))
