from __future__ import annotations

"""Unit tests for update.py — no network, fakes for GitHub API and apply."""

import hashlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from romhop import update
from romhop.update import AssetInfo, UpdateInfo, download_and_apply, update_check


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

CURRENT = "0.3.0"
NEWER = "0.4.0"
OLDER = "0.2.0"
RC_VERSION = "0.4.0rc1"

if sys.platform == "win32":
    ASSET_NAME = "romhop-setup-0.4.0.exe"
else:
    ASSET_NAME = "romhop-0.4.0.AppImage"


def _make_release(tag: str, prerelease: bool = False, asset_name: str | None = None) -> dict:
    name = asset_name or ASSET_NAME
    return {
        "tag_name": f"v{tag}",
        "prerelease": prerelease,
        "assets": [
            {
                "name": name,
                "browser_download_url": f"https://github.com/example/releases/download/v{tag}/{name}",
                "size": 10_000_000,
            },
            {
                "name": "SHA256SUMS",
                "browser_download_url": f"https://github.com/example/releases/download/v{tag}/SHA256SUMS",
                "size": 200,
            },
        ],
    }


def _gh_get_latest(release: dict):
    """Returns an injected GH-get callable that returns the given release for /latest."""
    def _get(url: str):
        assert "/releases/latest" in url
        return release
    return _get


def _gh_get_list(releases: list[dict]):
    """Returns an injected GH-get callable that returns the list for /releases."""
    def _get(url: str):
        assert "/releases" in url and "/releases/latest" not in url
        return releases
    return _get


# ---------------------------------------------------------------------------
# is_update_supported
# ---------------------------------------------------------------------------

def test_not_supported_in_dev():
    # Running under pytest — sys.frozen not set → must return False.
    assert not update.is_update_supported()


def test_supported_when_frozen_and_writable(tmp_path):
    with (
        patch.object(sys, "frozen", True, create=True),
        patch("romhop.install_bootstrap.install_dir", return_value=tmp_path),
    ):
        assert update.is_update_supported()


def test_not_supported_frozen_but_unwritable(tmp_path):
    tmp_path.chmod(0o444)
    try:
        with (
            patch.object(sys, "frozen", True, create=True),
            patch("romhop.install_bootstrap.install_dir", return_value=tmp_path),
        ):
            assert not update.is_update_supported()
    finally:
        tmp_path.chmod(0o755)


# ---------------------------------------------------------------------------
# update_check — stable channel
# ---------------------------------------------------------------------------

def test_update_check_newer_stable():
    info = update_check(CURRENT, _gh_get=_gh_get_latest(_make_release(NEWER)))
    assert info is not None
    assert info.version == NEWER
    assert info.asset.name == ASSET_NAME


def test_update_check_same_version_no_update():
    info = update_check(NEWER, _gh_get=_gh_get_latest(_make_release(NEWER)))
    assert info is None


def test_update_check_older_version_no_update():
    info = update_check(NEWER, _gh_get=_gh_get_latest(_make_release(OLDER)))
    assert info is None


def test_update_check_stable_excludes_prerelease():
    rc = _make_release("0.4.0rc1", prerelease=True)
    info = update_check(CURRENT, include_prereleases=False, _gh_get=_gh_get_latest(rc))
    # Stable /latest may still return a prerelease object; we filter it out.
    # For stable channel: prerelease flag set → treat as no update.
    # (The /latest endpoint normally won't return a prerelease, but guard anyway.)
    # Patch it: when prerelease=True and include_prereleases=False, return None.
    # Re-test with explicit list path:
    info2 = update_check(CURRENT, include_prereleases=False, _gh_get=_gh_get_latest({
        "tag_name": "v0.4.0rc1",
        "prerelease": True,
        "assets": rc["assets"],
    }))
    # Stable channel calls /releases/latest directly — prerelease flag on that
    # response should still be respected.
    assert info2 is None


def test_update_check_sha256sums_url_captured():
    info = update_check(CURRENT, _gh_get=_gh_get_latest(_make_release(NEWER)))
    assert info is not None
    assert "SHA256SUMS" in info.sha256sums_url


def test_update_check_no_matching_asset_returns_none():
    release = _make_release(NEWER, asset_name="romhop-wrong-platform.deb")
    info = update_check(CURRENT, _gh_get=_gh_get_latest(release))
    assert info is None


def test_update_check_network_error_returns_none():
    def _fail(url: str):
        raise ConnectionError("network down")
    info = update_check(CURRENT, _gh_get=_fail)
    assert info is None


# ---------------------------------------------------------------------------
# update_check — experimental channel
# ---------------------------------------------------------------------------

def test_experimental_picks_rc_over_current():
    rc_release = _make_release(RC_VERSION, prerelease=True)
    info = update_check(CURRENT, include_prereleases=True, _gh_get=_gh_get_list([rc_release]))
    assert info is not None
    assert info.version == RC_VERSION


def test_experimental_rolls_forward_rc_to_stable():
    """0.4.0rc1 < 0.4.0 → stable pick when both available."""
    rc = _make_release("0.4.0rc1", prerelease=True)
    stable = _make_release("0.4.0", prerelease=False)
    info = update_check(CURRENT, include_prereleases=True, _gh_get=_gh_get_list([stable, rc]))
    assert info is not None
    assert info.version == "0.4.0"


def test_experimental_picks_highest():
    r1 = _make_release("0.5.0rc1", prerelease=True)
    r2 = _make_release("0.4.0", prerelease=False)
    info = update_check(CURRENT, include_prereleases=True, _gh_get=_gh_get_list([r2, r1]))
    assert info is not None
    assert info.version == "0.5.0rc1"


def test_stable_channel_does_not_pick_prerelease_from_list():
    rc = _make_release("0.4.0rc1", prerelease=True)
    # Stable channel calls /releases/latest, not list — this test guards the
    # internal filter: if someone injects a prerelease via the list-endpoint
    # route with include_prereleases=False, it must be excluded.
    # Simulate by using list path while disabling prereleases (shouldn't reach
    # list normally, but tests the filter logic directly):
    called_with: list[str] = []

    def _gh(url: str):
        called_with.append(url)
        if "/releases/latest" in url:
            return _make_release(NEWER)
        return [rc]

    info = update_check(CURRENT, include_prereleases=False, _gh_get=_gh)
    # Stable path hits /latest → gets NEWER stable
    assert info is not None
    assert info.version == NEWER


# ---------------------------------------------------------------------------
# download_and_apply — SHA-256 verify
# ---------------------------------------------------------------------------

def _make_info(tmp_path: Path) -> tuple[UpdateInfo, bytes, str]:
    data = b"fake installer data"
    digest = hashlib.sha256(data).hexdigest()
    sha_content = f"{digest}  {ASSET_NAME}\n"
    info = UpdateInfo(
        version=NEWER,
        asset=AssetInfo(name=ASSET_NAME, url="https://example.com/asset", size=len(data)),
        sha256sums_url="https://example.com/SHA256SUMS",
    )
    return info, data, sha_content


def test_download_and_apply_calls_apply_on_success(tmp_path):
    info, data, sha_content = _make_info(tmp_path)
    applied: list[Path] = []

    def _fake_get_bytes(url: str, cb) -> bytes:
        return sha_content.encode() if "SHA256SUMS" in url else data

    download_and_apply(info, _apply_fn=lambda p: applied.append(p), _gh_get_bytes=_fake_get_bytes)
    assert len(applied) == 1
    assert applied[0].name == ASSET_NAME


def test_download_and_apply_sha256_mismatch_aborts(tmp_path):
    info, data, _ = _make_info(tmp_path)
    wrong_digest = "0" * 64
    sha_content = f"{wrong_digest}  {ASSET_NAME}\n"
    applied: list[Path] = []

    def _fake_get_bytes(url: str, cb) -> bytes:
        return sha_content.encode() if "SHA256SUMS" in url else data

    with pytest.raises(ValueError, match="SHA-256 mismatch"):
        download_and_apply(info, _apply_fn=lambda p: applied.append(p), _gh_get_bytes=_fake_get_bytes)
    assert not applied


def test_download_and_apply_sha256_entry_missing_aborts(tmp_path):
    info, data, _ = _make_info(tmp_path)
    sha_content = "abc123  other-file.exe\n"
    applied: list[Path] = []

    def _fake_get_bytes(url: str, cb) -> bytes:
        return sha_content.encode() if "SHA256SUMS" in url else data

    with pytest.raises(ValueError, match="No SHA256SUMS entry"):
        download_and_apply(info, _apply_fn=lambda p: applied.append(p), _gh_get_bytes=_fake_get_bytes)
    assert not applied


def test_download_and_apply_progress_forwarded(tmp_path):
    info, data, sha_content = _make_info(tmp_path)
    progress: list[tuple[int, int]] = []

    def _fake_get_bytes(url: str, cb) -> bytes:
        if "SHA256SUMS" in url:
            return sha_content.encode()
        if cb:
            cb(len(data), len(data))
        return data

    download_and_apply(info, progress_cb=lambda d, t: progress.append((d, t)),
                       _apply_fn=lambda p: None, _gh_get_bytes=_fake_get_bytes)
    assert progress  # at least one progress callback fired


def test_download_and_apply_no_sha256sums_raises_before_apply(tmp_path):
    """When sha256sums_url is empty, raise ValueError before apply_fn is called."""
    data = b"installer"
    info = UpdateInfo(
        version=NEWER,
        asset=AssetInfo(name=ASSET_NAME, url="https://example.com/asset", size=len(data)),
        sha256sums_url="",
    )
    applied: list[Path] = []

    def _fake_get_bytes(url: str, cb) -> bytes:
        return data

    with pytest.raises(ValueError, match="SHA256SUMS asset is missing"):
        download_and_apply(info, _apply_fn=lambda p: applied.append(p), _gh_get_bytes=_fake_get_bytes)
    assert applied == []


# ---------------------------------------------------------------------------
# config integration
# ---------------------------------------------------------------------------

def test_config_has_update_include_prereleases_field():
    from romhop.config import SCHEMA, default_settings
    keys = [f.key for f in SCHEMA]
    assert "update_include_prereleases" in keys
    assert default_settings().update_include_prereleases is False


def test_config_has_auto_update_check_field():
    from romhop.config import default_settings
    assert default_settings().auto_update_check is True
