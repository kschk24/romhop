from __future__ import annotations

"""Qt-free GitHub-Releases self-updater for frozen installs.

Only active when running as a frozen PyInstaller bundle with a writable
install dir.  In dev/pip ``is_update_supported()`` returns False so all
entry points are no-ops.

Public surface:
  is_update_supported() -> bool
  update_check(current_version, *, include_prereleases) -> UpdateInfo | None
  download_and_apply(info, progress_cb, *, _apply_fn=None) -> None

All callables accept injectable fakes for unit tests (no network required).
"""

import hashlib
import logging
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

import httpx
from packaging.version import Version

from romhop import install_bootstrap

_OWNER = "kschk24"
_REPO = "romhop"
_GH_API = "https://api.github.com"
_API_TIMEOUT = 10  # seconds

# Asset filename patterns per OS
_WIN_PATTERN = "-setup-"
_LINUX_SUFFIX = ".AppImage"


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AssetInfo:
    name: str
    url: str
    size: int


@dataclass(frozen=True)
class UpdateInfo:
    version: str          # e.g. "0.4.0"
    asset: AssetInfo      # OS installer asset
    sha256sums_url: str   # URL to SHA256SUMS file in the same release


# ---------------------------------------------------------------------------
# Frozen-install gate
# ---------------------------------------------------------------------------


def is_update_supported() -> bool:
    """True only when running frozen and the install dir is writable."""
    if not getattr(sys, "frozen", False):
        return False
    try:
        d = install_bootstrap.install_dir()
        return os.access(d, os.W_OK)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Version check
# ---------------------------------------------------------------------------


def _pick_asset(assets: list[dict]) -> AssetInfo | None:
    """Select the OS-appropriate installer asset from a release's asset list."""
    for a in assets:
        name: str = a.get("name", "")
        if sys.platform == "win32" and _WIN_PATTERN in name and name.endswith(".exe"):
            return AssetInfo(name=name, url=a["browser_download_url"], size=a.get("size", 0))
        if sys.platform != "win32" and name.endswith(_LINUX_SUFFIX):
            return AssetInfo(name=name, url=a["browser_download_url"], size=a.get("size", 0))
    return None


def _sha256sums_url(assets: list[dict]) -> str:
    for a in assets:
        if a.get("name") == "SHA256SUMS":
            return a["browser_download_url"]
    return ""


def update_check(
    current_version: str,
    *,
    include_prereleases: bool = False,
    _gh_get: Callable[[str], dict | list] | None = None,
) -> UpdateInfo | None:
    """Check GitHub Releases for a newer version.

    Returns UpdateInfo when a newer release is found, else None.
    Network errors are caught and logged; caller always gets None on failure.

    _gh_get: injectable for unit tests (str url -> parsed JSON).
    """
    def _default_get(url: str) -> dict | list:
        headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
        resp = httpx.get(url, headers=headers, timeout=_API_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        return resp.json()

    gh_get = _gh_get or _default_get

    try:
        current = Version(current_version)

        if not include_prereleases:
            data = gh_get(f"{_GH_API}/repos/{_OWNER}/{_REPO}/releases/latest")
            if not isinstance(data, dict):
                raise TypeError(f"expected dict from /releases/latest, got {type(data)}")
            releases = [data]
        else:
            data = gh_get(f"{_GH_API}/repos/{_OWNER}/{_REPO}/releases")
            if not isinstance(data, list):
                raise TypeError(f"expected list from /releases, got {type(data)}")
            releases = data

        best_version: Version | None = None
        best_release: dict | None = None

        for rel in releases:
            if not isinstance(rel, dict):
                continue
            if not include_prereleases and rel.get("prerelease", False):
                continue
            tag: str = rel.get("tag_name", "")
            ver_str = tag.lstrip("v")
            try:
                v = Version(ver_str)
            except Exception:
                continue
            if v > current:
                if best_version is None or v > best_version:
                    best_version = v
                    best_release = rel

        if best_release is None or best_version is None:
            return None

        assets: list[dict] = best_release.get("assets", [])
        asset = _pick_asset(assets)
        if asset is None:
            return None

        sha_url = _sha256sums_url(assets)
        return UpdateInfo(
            version=str(best_version),
            asset=asset,
            sha256sums_url=sha_url,
        )

    except Exception as exc:
        logger.warning("Update check failed: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Download, verify, and apply
# ---------------------------------------------------------------------------


def _verify_sha256(digest: str, sha256sums_content: str, asset_name: str) -> None:
    """Raise ValueError if digest doesn't match the SHA256SUMS entry for asset_name."""
    expected: str | None = None
    for line in sha256sums_content.splitlines():
        parts = line.split(None, 1)
        if len(parts) == 2 and parts[1].strip().lstrip("*") == asset_name:
            expected = parts[0].strip().lower()
            break
    if expected is None:
        raise ValueError(f"No SHA256SUMS entry for {asset_name!r}")
    if digest.lower() != expected:
        raise ValueError(f"SHA-256 mismatch for {asset_name}: got {digest}, expected {expected}")


def _apply_installer(path: Path) -> None:
    """Run the OS installer silently; raises on non-zero exit."""
    if sys.platform == "win32":
        cmd = [str(path), "/VERYSILENT", "/NORESTART", "/SUPPRESSMSGBOXES"]
        env = None
    else:
        path.chmod(path.stat().st_mode | 0o111)
        cmd = [str(path)]  # AppRun hardcodes --appimage-bootstrap; runtime rejects unknown --appimage-* flags
        # PyInstaller prepends _internal/ to LD_LIBRARY_PATH so its bundled
        # libs load.  The installer subprocess inherits this and its /bin/sh
        # picks up the bundled readline, causing a symbol-lookup error and
        # exit code 127.  Restore the original LD_LIBRARY_PATH (PyInstaller
        # saves it as LD_LIBRARY_PATH_ORIG) so the installer sees system libs.
        env = os.environ.copy()
        orig = env.pop("LD_LIBRARY_PATH_ORIG", None)
        if orig is not None:
            env["LD_LIBRARY_PATH"] = orig
        else:
            env.pop("LD_LIBRARY_PATH", None)

    result = subprocess.run(cmd, check=False, env=env)
    if result.returncode != 0:
        raise RuntimeError(f"Installer exited with code {result.returncode}")


def download_and_apply(
    info: UpdateInfo,
    progress_cb: Callable[[int, int], None] | None = None,
    *,
    _apply_fn: Callable[[Path], None] | None = None,
    _gh_get_bytes: Callable[[str, Callable[[int, int], None] | None], bytes] | None = None,
    _gh_stream_asset: Callable[[str, Path, Callable[[int, int], None] | None], str] | None = None,
) -> None:
    """Stream installer asset to temp, verify SHA-256, exec installer silently.

    progress_cb(bytes_done, bytes_total) — called during streaming.
    _apply_fn / _gh_get_bytes / _gh_stream_asset: injectable fakes for unit tests.
    _gh_stream_asset(url, dest_path, cb) -> hex_digest — streams asset to dest_path,
    computing SHA-256 incrementally; returns hex digest.
    """
    apply_fn = _apply_fn or _apply_installer

    if not info.sha256sums_url:
        raise ValueError(
            "SHA256SUMS asset is missing from this release; "
            "refusing to apply an unverified installer"
        )

    def _default_get_bytes(url: str, cb: Callable[[int, int], None] | None) -> bytes:
        resp = httpx.get(url, timeout=_API_TIMEOUT, follow_redirects=True)
        resp.raise_for_status()
        return resp.content

    def _default_stream_asset(
        url: str,
        dest: Path,
        cb: Callable[[int, int], None] | None,
    ) -> str:
        hasher = hashlib.sha256()
        done = 0
        with httpx.stream("GET", url, timeout=None, follow_redirects=True) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            with dest.open("wb") as fh:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    fh.write(chunk)
                    hasher.update(chunk)
                    done += len(chunk)
                    if cb:
                        cb(done, total)
        return hasher.hexdigest()

    get_bytes = _gh_get_bytes or _default_get_bytes
    stream_asset = _gh_stream_asset or _default_stream_asset

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        # Fetch SHA256SUMS first (small file — buffer ok)
        sha_content = get_bytes(info.sha256sums_url, None).decode()

        # Stream installer asset directly to .part file; hash computed during download
        part_path = tmp / (info.asset.name + ".part")
        digest = stream_asset(info.asset.url, part_path, progress_cb)

        # Rename .part → final
        final_path = tmp / info.asset.name
        part_path.rename(final_path)

        # Verify using pre-computed digest (no full file re-read)
        _verify_sha256(digest, sha_content, info.asset.name)

        # Apply
        apply_fn(final_path)
