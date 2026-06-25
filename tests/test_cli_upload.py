from __future__ import annotations

from dataclasses import dataclass, field

import pytest
from typer.testing import CliRunner

from romhop import cli
from romhop.local_index import LocalGame, MatchResult

runner = CliRunner()


@dataclass
class _RecoverInfo:
    was_dirty: bool = False


class _FakePlatforms:
    def list_platforms(self):
        return [{"id": 1, "slug": "snes", "fs_slug": "snes"}]


def _make_local(system: str, game_name: str) -> LocalGame:
    return LocalGame(system=system, game_name=game_name,
                     file_names=[game_name + ".sfc"], match_key=game_name.lower())


def _make_settings(tmp_path):
    settings = cli.config.default_settings()
    settings.romm_url = "http://romm.test"
    settings.roms_root = tmp_path
    return settings


def _patch_common(monkeypatch, tmp_path, *, matched=None, unmatched=None):
    """Wire up the minimal mocks every upload-command test needs."""
    matched = matched or []
    unmatched = unmatched or []

    settings = _make_settings(tmp_path)
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: "rmm_x")

    class FakeClient(_FakePlatforms):
        def __init__(self, *a, **k): pass
        def list_roms(self, search_term=None): return []

    monkeypatch.setattr(cli, "RommClient", FakeClient)

    result = MatchResult(matched=matched, unmatched=unmatched)
    monkeypatch.setattr(cli, "index_local_library", lambda root, ov: [])
    monkeypatch.setattr(cli, "match_to_roms", lambda l, r, ov: result)

    import romhop.upload_session as _sess
    monkeypatch.setattr(_sess, "recover", lambda client: _RecoverInfo())

    return settings


# ---------------------------------------------------------------------------
# AC#2: variadic name filter
# ---------------------------------------------------------------------------

def test_upload_name_filter_matches_substring(monkeypatch, tmp_path):
    """Only games whose game_name contains the given substring are offered."""
    unmatched = [
        _make_local("snes", "Zelda - A Link to the Past"),
        _make_local("snes", "Super Mario World"),
        _make_local("snes", "Metroid"),
    ]
    _patch_common(monkeypatch, tmp_path, unmatched=unmatched)

    batch_seen = []

    def fake_discover(local_games, romm_platforms, overrides):
        batch_seen.extend(local_games)
        from romhop.upload import UploadCandidates
        return UploadCandidates(
            resolvable=[(g, {"id": 1, "slug": "snes"}) for g in local_games],
            missing_platform=[],
            unresolvable=[],
        )

    import romhop.upload as _up
    monkeypatch.setattr(_up, "discover_uploadable", fake_discover)
    monkeypatch.setattr(_up, "run_upload_batch", lambda *a, **k: None)
    # Force non-TTY so picker is skipped.
    monkeypatch.setattr(cli, "_stdin_isatty", lambda: False)

    result = runner.invoke(cli.app, ["upload", "zelda", "--yes"])

    assert result.exit_code == 0, result.output
    assert len(batch_seen) == 1
    assert batch_seen[0].game_name == "Zelda - A Link to the Past"


def test_upload_name_filter_no_match_exits_gracefully(monkeypatch, tmp_path):
    unmatched = [_make_local("snes", "Super Mario World")]
    _patch_common(monkeypatch, tmp_path, unmatched=unmatched)

    result = runner.invoke(cli.app, ["upload", "zelda"])

    assert result.exit_code == 0
    assert "No unmatched" in result.output


def test_upload_name_filter_multi_term_deduped(monkeypatch, tmp_path):
    """Multiple name terms are OR-ed; duplicates matching several terms appear once."""
    zelda = _make_local("snes", "Zelda")
    mario = _make_local("snes", "Mario")
    _patch_common(monkeypatch, tmp_path, unmatched=[zelda, mario])

    batch_seen = []

    def fake_discover(local_games, romm_platforms, overrides):
        batch_seen.extend(local_games)
        from romhop.upload import UploadCandidates
        return UploadCandidates(
            resolvable=[(g, {"id": 1, "slug": "snes"}) for g in local_games],
            missing_platform=[], unresolvable=[],
        )

    import romhop.upload as _up
    monkeypatch.setattr(_up, "discover_uploadable", fake_discover)
    monkeypatch.setattr(_up, "run_upload_batch", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_stdin_isatty", lambda: False)

    result = runner.invoke(cli.app, ["upload", "zelda", "mario", "--yes"])

    assert result.exit_code == 0, result.output
    assert len(batch_seen) == 2
    names = {g.game_name for g in batch_seen}
    assert names == {"Zelda", "Mario"}


# ---------------------------------------------------------------------------
# AC#3: --platform filter
# ---------------------------------------------------------------------------

def test_upload_platform_filter_restricts_systems(monkeypatch, tmp_path):
    unmatched = [
        _make_local("snes", "Super Mario World"),
        _make_local("gba", "Metroid Fusion"),
    ]
    _patch_common(monkeypatch, tmp_path, unmatched=unmatched)

    batch_seen = []

    def fake_discover(local_games, romm_platforms, overrides):
        batch_seen.extend(local_games)
        from romhop.upload import UploadCandidates
        return UploadCandidates(
            resolvable=[(g, {"id": 1, "slug": "snes"}) for g in local_games],
            missing_platform=[], unresolvable=[],
        )

    import romhop.upload as _up
    monkeypatch.setattr(_up, "discover_uploadable", fake_discover)
    monkeypatch.setattr(_up, "run_upload_batch", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_stdin_isatty", lambda: False)

    result = runner.invoke(cli.app, ["upload", "--platform", "snes", "--yes"])

    assert result.exit_code == 0, result.output
    assert len(batch_seen) == 1
    assert batch_seen[0].system == "snes"


def test_upload_platform_filter_case_insensitive(monkeypatch, tmp_path):
    unmatched = [_make_local("SNES", "Mario")]
    _patch_common(monkeypatch, tmp_path, unmatched=unmatched)

    batch_seen = []

    def fake_discover(local_games, romm_platforms, overrides):
        batch_seen.extend(local_games)
        from romhop.upload import UploadCandidates
        return UploadCandidates(
            resolvable=[(g, {"id": 1, "slug": "snes"}) for g in local_games],
            missing_platform=[], unresolvable=[],
        )

    import romhop.upload as _up
    monkeypatch.setattr(_up, "discover_uploadable", fake_discover)
    monkeypatch.setattr(_up, "run_upload_batch", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_stdin_isatty", lambda: False)

    result = runner.invoke(cli.app, ["upload", "--platform", "snes", "--yes"])

    assert result.exit_code == 0, result.output
    assert len(batch_seen) == 1


def test_upload_platform_filter_repeatable(monkeypatch, tmp_path):
    unmatched = [
        _make_local("snes", "Mario"),
        _make_local("gba", "Metroid"),
        _make_local("nes", "Contra"),
    ]
    _patch_common(monkeypatch, tmp_path, unmatched=unmatched)

    batch_seen = []

    def fake_discover(local_games, romm_platforms, overrides):
        batch_seen.extend(local_games)
        from romhop.upload import UploadCandidates
        return UploadCandidates(
            resolvable=[(g, {"id": 1, "slug": "snes"}) for g in local_games],
            missing_platform=[], unresolvable=[],
        )

    import romhop.upload as _up
    monkeypatch.setattr(_up, "discover_uploadable", fake_discover)
    monkeypatch.setattr(_up, "run_upload_batch", lambda *a, **k: None)
    monkeypatch.setattr(cli, "_stdin_isatty", lambda: False)

    result = runner.invoke(cli.app, ["upload", "--platform", "snes", "--platform", "gba", "--yes"])

    assert result.exit_code == 0, result.output
    systems = {g.system for g in batch_seen}
    assert systems == {"snes", "gba"}


# ---------------------------------------------------------------------------
# AC#4 / AC#5: --yes non-interactive + discovery-only (no stray cache writes)
# ---------------------------------------------------------------------------

def test_upload_yes_skips_picker_and_confirm(monkeypatch, tmp_path):
    """--yes uploads without any interactive prompts."""
    unmatched = [_make_local("snes", "Mario")]
    settings = _patch_common(monkeypatch, tmp_path, unmatched=unmatched)

    batch_called = {}

    def fake_discover(local_games, romm_platforms, overrides):
        from romhop.upload import UploadCandidates
        return UploadCandidates(
            resolvable=[(g, {"id": 1, "slug": "snes"}) for g in local_games],
            missing_platform=[], unresolvable=[],
        )

    def fake_run_batch(selected, client, **kwargs):
        batch_called["selected"] = selected

    import romhop.upload as _up
    monkeypatch.setattr(_up, "discover_uploadable", fake_discover)
    monkeypatch.setattr(_up, "run_upload_batch", fake_run_batch)

    result = runner.invoke(cli.app, ["upload", "--yes"])

    assert result.exit_code == 0, result.output
    assert "selected" in batch_called
    assert len(batch_called["selected"]) == 1


def test_upload_discovery_does_not_seed_cache_for_matched(monkeypatch, tmp_path):
    """Matched games are discovered but cache.add is never called for them."""
    matched_local = _make_local("snes", "Matched Game")

    class FakeRom:
        id = 42
        name = "Matched Game"
        platform_slug = "snes"
        fs_name_no_ext = "Matched Game"

    matched = [(matched_local, FakeRom())]
    unmatched = [_make_local("snes", "Unmatched Game")]
    settings = _patch_common(monkeypatch, tmp_path, matched=matched, unmatched=unmatched)

    cache_adds: list = []

    class FakeCache:
        def add(self, entry): cache_adds.append(entry)
        def save(self): pass

    monkeypatch.setattr(cli, "MappingCache", lambda path: FakeCache())

    def fake_discover(local_games, romm_platforms, overrides):
        from romhop.upload import UploadCandidates
        return UploadCandidates(
            resolvable=[(g, {"id": 1, "slug": "snes"}) for g in local_games],
            missing_platform=[], unresolvable=[],
        )

    upload_batch_called = {}

    def fake_run_batch(selected, client, **kwargs):
        upload_batch_called["selected"] = selected

    import romhop.upload as _up
    monkeypatch.setattr(_up, "discover_uploadable", fake_discover)
    monkeypatch.setattr(_up, "run_upload_batch", fake_run_batch)

    result = runner.invoke(cli.app, ["upload", "--yes"])

    assert result.exit_code == 0, result.output
    # Cache must not be seeded for matched-only games — upload command is discovery-only.
    assert cache_adds == [], f"Unexpected cache.add calls: {cache_adds}"
    # Only the unmatched game reaches run_upload_batch.
    assert "selected" in upload_batch_called
    assert len(upload_batch_called["selected"]) == 1
    assert upload_batch_called["selected"][0][0].game_name == "Unmatched Game"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_upload_no_roms_root_exits_1(monkeypatch):
    settings = cli.config.default_settings()  # roms_root == None
    monkeypatch.setattr(cli.config, "load_settings", lambda: settings)
    monkeypatch.setattr(cli.config, "get_token", lambda: "rmm_x")

    result = runner.invoke(cli.app, ["upload"])

    assert result.exit_code == 1
    assert "ROMs folder" in result.output


def test_upload_no_unmatched_after_match(monkeypatch, tmp_path):
    """All local games matched → no games to upload."""
    _patch_common(monkeypatch, tmp_path, unmatched=[])

    result = runner.invoke(cli.app, ["upload"])

    assert result.exit_code == 0
    assert "No unmatched" in result.output


def test_upload_recover_dirty_prints_note(monkeypatch, tmp_path):
    _patch_common(monkeypatch, tmp_path, unmatched=[])

    import romhop.upload_session as _sess
    monkeypatch.setattr(_sess, "recover", lambda client: _RecoverInfo(was_dirty=True))

    result = runner.invoke(cli.app, ["upload"])

    assert "interrupted" in result.output.lower()
    assert "upload" in result.output.lower()
