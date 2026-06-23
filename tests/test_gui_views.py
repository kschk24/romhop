from PySide6.QtCore import QObject, Signal

from romhop.gui import library_view
from romhop.gui.library_view import LibraryView
from romhop.romm_client import Rom


def _rom(name, slug):
    return Rom(id=hash((name, slug)) & 0xffff, name=name, platform_slug=slug,
               fs_name=name, fs_name_no_ext=name, file_names=[name])


def test_platforms_from_roms_sorted_unique():
    roms = [_rom("A", "snes"), _rom("B", "nes"), _rom("C", "snes")]
    assert library_view.platforms_from_roms(roms) == ["nes", "snes"]


# --- filter_games tests (Step 1 replacements) ---

def test_filter_games_all_platforms_sorted_asc():
    roms = [_rom("Sonic", "genesis"), _rom("Mario", "nes"), _rom("Zelda", "nes")]
    out = library_view.filter_games(roms, platform=None, query="")
    assert [r.name for r in out] == ["Mario", "Sonic", "Zelda"]


def test_filter_games_platform_scopes():
    roms = [_rom("Sonic", "genesis"), _rom("Mario", "nes")]
    out = library_view.filter_games(roms, platform="genesis", query="")
    assert [r.name for r in out] == ["Sonic"]


def test_filter_games_query_combines_with_platform():
    roms = [_rom("Sonic", "genesis"), _rom("Streets of Rage", "genesis")]
    out = library_view.filter_games(roms, platform="genesis", query="so")
    assert [r.name for r in out] == ["Sonic"]


def test_filter_games_sort_desc():
    roms = [_rom("Mario", "nes"), _rom("Zelda", "nes")]
    out = library_view.filter_games(roms, platform=None, query="", sort="desc")
    assert [r.name for r in out] == ["Zelda", "Mario"]


def test_filter_games_downloaded_modes():
    a, b = _rom("Sonic", "genesis"), _rom("Mario", "nes")
    ids = {a.id}
    only_dl = library_view.filter_games([a, b], platform=None, query="",
                                        downloaded_ids=ids, downloaded_mode="downloaded")
    assert [r.name for r in only_dl] == ["Sonic"]
    only_missing = library_view.filter_games([a, b], platform=None, query="",
                                             downloaded_ids=ids, downloaded_mode="missing")
    assert [r.name for r in only_missing] == ["Mario"]


# --- LibraryView widget tests (Step 3 replacements) ---

def test_library_view_populates_all_platforms(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    assert {rom.name for _, rom in view._checks.values()} == {"Sonic", "Mario"}
    check, rom = next((c, r) for c, r in view._checks.values() if r.name == "Sonic")
    check.setChecked(True)
    assert view.selected_roms()[0].name == "Sonic"


def test_platform_filter_scopes_grid(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    view.set_platform_filter("genesis")
    assert {rom.name for _, rom in view._checks.values()} == {"Sonic"}


def test_selection_survives_platform_filter(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    check, _ = next((c, r) for c, r in view._checks.values() if r.name == "Sonic")
    check.setChecked(True)
    view.set_platform_filter("nes")
    check2, _ = next((c, r) for c, r in view._checks.values() if r.name == "Mario")
    check2.setChecked(True)
    assert sorted(r.name for r in view.selected_roms()) == ["Mario", "Sonic"]


def test_tiles_have_fixed_size_regardless_of_game_count(qtbot):
    from romhop.gui.library_view import CELL_HEIGHT, CELL_WIDTH, LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom(f"G{i}", "nds") for i in range(30)] + [_rom("Solo", "threeds")])
    assert view._cells
    for c in view._cells:
        assert c.minimumHeight() == CELL_HEIGHT and c.maximumHeight() == CELL_HEIGHT
        assert c.minimumWidth() == CELL_WIDTH and c.maximumWidth() == CELL_WIDTH


def test_columns_for_width_scales_and_floors_at_one():
    # Wider viewport -> more columns; never fewer than one even when tiny.
    assert library_view.columns_for_width(640, cell_width=160) == 4
    assert library_view.columns_for_width(330, cell_width=160) == 2
    assert library_view.columns_for_width(50, cell_width=160) == 1
    assert library_view.columns_for_width(0, cell_width=160) == 1


def test_grid_reflows_on_resize(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom(f"G{i}", "genesis") for i in range(12)])
    view.resize(960, 600)
    view.show()
    qtbot.waitExposed(view)
    wide_cols = view._cols
    view.resize(280, 600)
    qtbot.wait(20)
    narrow_cols = view._cols
    assert wide_cols > narrow_cols
    assert narrow_cols >= 1


def test_library_view_selection_survives_filter(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Streets of Rage", "genesis")])
    for check, rom in list(view._checks.values()):
        if rom.name == "Sonic":
            check.setChecked(True)
    # Narrow the view to just "Sonic"; its checked state must persist.
    view.filter("Sonic")
    assert [r.name for r in view.selected_roms()] == ["Sonic"]


def test_cells_have_cover_label_placeholder(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis")])
    # Each game has a registered cover label, blank (null pixmap) until loaded.
    assert view._cover_labels
    label = next(iter(view._cover_labels.values()))
    assert label.pixmap().isNull()


def test_apply_cover_sets_pixmap(qtbot, tmp_path):
    from PySide6.QtGui import QImage, QPixmap
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis")])
    rom_id = next(iter(view._cover_labels))

    # Build a real QImage (as the loader now emits).
    src = QPixmap(8, 8)
    src.fill()
    image = src.toImage()
    view._apply_cover(rom_id, image)

    assert not view._cover_labels[rom_id].pixmap().isNull()
    assert rom_id in view._pixmap_cache


def test_apply_cover_ignores_unknown_rom(qtbot):
    from PySide6.QtGui import QImage, QPixmap
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis")])
    # Stale emit for a rom not on screen: pass a real QImage, must be a no-op.
    src = QPixmap(4, 4)
    src.fill()
    image = src.toImage()
    unknown_id = 999999
    view._apply_cover(unknown_id, image)
    assert unknown_id not in view._pixmap_cache


def test_unchecking_removes_from_global_selection(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Mario", "nes")])
    check, _ = next(iter(view._checks.values()))
    check.setChecked(True)
    assert len(view.selected_roms()) == 1
    check.setChecked(False)
    assert view.selected_roms() == []


def test_switching_platform_does_not_drop_running_cover_loader(qtbot):
    # Regression: set_roms overwrote the single _cover_loader slot, dropping the
    # previous loader's last reference while its QThread was still running -> GC
    # destroyed it -> "QThread: Destroyed while thread is still running" abort.
    import threading
    from romhop.gui.library_view import LibraryView

    started = threading.Event()
    release = threading.Event()

    def slow_provider(rom):
        started.set()
        release.wait(2.0)        # block so the loader stays running
        return None

    view = LibraryView(cover_provider=slow_provider)
    qtbot.addWidget(view)
    view.set_roms([_rom("Sonic", "genesis"), _rom("Tails", "genesis")])
    assert started.wait(2.0)     # first loader is running
    first = view._cover_loader
    assert first in view._cover_loaders

    # Switch platform while the first loader is mid-run.
    view.set_roms([_rom("Mario", "nes")])

    # The old loader must be asked to stop AND kept referenced until it finishes,
    # never silently dropped while running.
    assert first.isInterruptionRequested()
    assert first in view._cover_loaders

    release.set()
    qtbot.waitUntil(lambda: first not in view._cover_loaders, timeout=2000)
    assert not first.isRunning()


# --- Indicator tests (Step 6) ---

def test_tile_shows_platform_pill(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView(platform_label=lambda rom: "Game Boy")
    qtbot.addWidget(view)
    view.set_roms([_rom("Tetris", "gb")])
    pill = next(iter(view._pills.values()))
    assert pill.text() == "Game Boy"


def test_downloaded_tile_gets_ribbon_others_do_not(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    a, b = _rom("Sonic", "genesis"), _rom("Mario", "nes")
    view.set_roms([a, b])
    view.set_downloaded({a.id})
    assert a.id in view._ribbons
    assert b.id not in view._ribbons


def test_downloaded_filter_hides_missing(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    a, b = _rom("Sonic", "genesis"), _rom("Mario", "nes")
    view.set_roms([a, b])
    view.set_downloaded({a.id})
    view.set_downloaded_filter("downloaded")
    assert {rom.name for _, rom in view._checks.values()} == {"Sonic"}


def test_set_roms_clears_stale_downloaded_ids(qtbot):
    from romhop.gui.library_view import LibraryView
    view = LibraryView()
    qtbot.addWidget(view)
    a = _rom("Sonic", "genesis")
    view.set_roms([a])
    view.set_downloaded({a.id})
    assert a.id in view._ribbons
    # Reload with a different library; the old downloaded id must not persist.
    b = _rom("Mario", "nes")
    view.set_roms([b])
    assert view._downloaded_ids == set()
    assert view._ribbons == {}


def test_cover_pixmap_cache_reused_across_platform_switch(qtbot, tmp_path):
    """Cache hit on platform switch: provider not called again, pixmap instant."""
    from PySide6.QtGui import QPixmap
    from romhop.gui.library_view import LibraryView

    # Write a real PNG so QImage decode succeeds inside CoverLoader.
    img_a = tmp_path / "rom_a.png"
    img_b = tmp_path / "rom_b.png"
    for p in (img_a, img_b):
        px = QPixmap(8, 8)
        px.fill()
        assert px.save(str(p), "PNG")

    rom_a = _rom("Sonic", "genesis")
    rom_b = _rom("Mario", "nes")

    call_counts: dict[int, int] = {}

    def provider(rom):
        call_counts[rom.id] = call_counts.get(rom.id, 0) + 1
        if rom.id == rom_a.id:
            return img_a
        if rom.id == rom_b.id:
            return img_b
        return None

    view = LibraryView(cover_provider=provider)
    qtbot.addWidget(view)
    view.set_roms([rom_a, rom_b])

    # Filter to platform A and wait until rom_a is in the pixmap cache.
    view.set_platform_filter("genesis")
    qtbot.waitUntil(lambda: rom_a.id in view._pixmap_cache, timeout=3000)

    count_a_after_first = call_counts.get(rom_a.id, 0)
    assert count_a_after_first >= 1  # provider was called at least once

    # Switch to platform B then back to A.
    view.set_platform_filter("nes")
    view.set_platform_filter("genesis")

    # rom_a's label must show its pixmap immediately (cache hit, no new decode).
    label = view._cover_labels.get(rom_a.id)
    assert label is not None
    assert not label.pixmap().isNull()

    # Provider must NOT have been called again for rom_a.
    assert call_counts.get(rom_a.id, 0) == count_a_after_first


def test_settings_form_has_download_rate_limit_field(qtbot, monkeypatch):
    from romhop.gui.settings_view import SettingsView
    from romhop import config
    # _on_save persists via config.save_settings — stub it so the test never
    # writes the real user settings file.
    monkeypatch.setattr(config, "save_settings", lambda s: None)
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    assert "Download limit (KB/s, 0 = unlimited)" in view._edits
    view._edits["Download limit (KB/s, 0 = unlimited)"].setText("256")
    view._on_save()
    assert view.current_settings().download_rate_limit_kbps == 256


# --- logging GUI controls (TASK-032) ---

def test_settings_debug_logging_checkbox_auto_rendered(qtbot, monkeypatch):
    from romhop.gui.settings_view import SettingsView
    from romhop import config
    monkeypatch.setattr(config, "save_settings", lambda s: None)
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    assert "Detailed logging (debug)" in view._edits


def test_settings_debug_logging_toggle_persists(qtbot, monkeypatch):
    from romhop.gui.settings_view import SettingsView
    from romhop import config
    from PySide6.QtWidgets import QCheckBox
    monkeypatch.setattr(config, "save_settings", lambda s: None)
    view = SettingsView(config.default_settings())
    qtbot.addWidget(view)
    cb = view._edits["Detailed logging (debug)"]
    assert isinstance(cb, QCheckBox)
    assert not cb.isChecked()  # default False
    cb.setChecked(True)
    view._on_save()
    assert view.current_settings().debug_logging is True


def test_settings_debug_logging_live_apply_calls_configure_logging(qtbot, monkeypatch):
    """Saving debug_logging=True must reconfigure the root logger to DEBUG."""
    from romhop.gui.settings_view import SettingsView
    from romhop import config
    import romhop.logging_setup as ls
    calls = []
    monkeypatch.setattr(config, "save_settings", lambda s: None)
    monkeypatch.setattr(ls, "configure_logging", lambda **kw: calls.append(kw))
    monkeypatch.setattr(config, "get_token", lambda: "tok")

    apply_calls = []

    def fake_apply(new_settings):
        # Simulate what app.py does: call configure_logging when debug changes.
        import romhop.logging_setup as _ls
        _ls.configure_logging(
            debug=new_settings.debug_logging,
            verbose=False,
            token=config.get_token() or "",
            romm_url=new_settings.romm_url,
        )
        apply_calls.append(new_settings)

    from romhop.gui.main_window import MainWindow
    settings = config.default_settings()
    w = MainWindow(settings=settings, apply_settings=fake_apply)
    qtbot.addWidget(w)

    cb = w.settings_view._edits["Detailed logging (debug)"]
    cb.setChecked(True)
    w.settings_view._on_save()

    assert apply_calls, "apply_settings never called"
    assert calls, "configure_logging never called after save"
    assert calls[-1]["debug"] is True


def test_settings_open_log_folder_invokes_callable(qtbot, monkeypatch):
    from romhop.gui.settings_view import SettingsView
    from romhop import config
    monkeypatch.setattr(config, "save_settings", lambda s: None)
    called = []
    view = SettingsView(config.default_settings(), open_log_dir_fn=lambda: called.append(1))
    qtbot.addWidget(view)
    view.open_log_btn.click()
    assert called == [1]


def test_settings_export_logs_invokes_callable(qtbot, monkeypatch):
    from pathlib import Path
    from romhop.gui.settings_view import SettingsView
    from romhop import config
    monkeypatch.setattr(config, "save_settings", lambda s: None)
    received = []

    def fake_export(dest):
        received.append(dest)

    view = SettingsView(config.default_settings(), export_logs_fn=fake_export)
    qtbot.addWidget(view)

    dest = Path("/tmp/test-romhop-logs.zip")
    monkeypatch.setattr(
        "romhop.gui.settings_view.QFileDialog.getSaveFileName",
        lambda *a, **kw: (str(dest), "Zip files (*.zip)"),
    )
    view.export_logs_btn.click()
    assert received == [dest]


def test_tile_body_click_emits_tile_activated(qtbot):
    view = LibraryView()
    qtbot.addWidget(view)
    rom = _rom("Sonic", "genesis")
    view.set_roms([rom])
    captured = []
    view.tile_activated.connect(captured.append)
    view._activate_rom(rom.id)
    assert captured == [rom]
    assert view.selected_roms() == []  # body click must NOT select


def test_context_menu_action_emits_action_requested(qtbot):
    view = LibraryView()
    qtbot.addWidget(view)
    rom = _rom("Sonic", "genesis")
    view.set_roms([rom])
    captured = []
    view.action_requested.connect(lambda name, r: captured.append((name, r.id)))
    view._emit_action("pull", rom.id)
    assert captured == [("pull", rom.id)]


def test_settings_export_logs_no_op_when_cancelled(qtbot, monkeypatch):
    from romhop.gui.settings_view import SettingsView
    from romhop import config
    monkeypatch.setattr(config, "save_settings", lambda s: None)
    received = []

    view = SettingsView(config.default_settings(), export_logs_fn=lambda p: received.append(p))
    qtbot.addWidget(view)
    # Simulate cancel: getSaveFileName returns empty string.
    monkeypatch.setattr(
        "romhop.gui.settings_view.QFileDialog.getSaveFileName",
        lambda *a, **kw: ("", ""),
    )
    view.export_logs_btn.click()
    assert received == []


# --- bulk Pull button (TASK-008) ---

class _FakePullWorker(QObject):
    """Runs the pull_fn synchronously on start() so the bulk-pull dispatch can
    be tested without a live QThread or modal conflict dialog."""

    conflict = Signal(object, object, object)
    done = Signal(dict)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, pull_fn, parent=None):
        super().__init__(parent)
        self._pull_fn = pull_fn

    def start(self):
        try:
            result = self._pull_fn(lambda *a: False)
        except Exception as exc:  # mirror PullWorker.run
            self.failed.emit(str(exc))
        else:
            self.done.emit(result)
        self.finished.emit()


def _make_main_window(qtbot, monkeypatch, pull_action):
    from romhop import config
    from romhop.gui import main_window
    from romhop.gui.main_window import MainWindow
    monkeypatch.setattr(main_window, "PullWorker", _FakePullWorker)
    monkeypatch.setattr(main_window.QMessageBox, "information", lambda *a, **kw: None)
    w = MainWindow(settings=config.default_settings(),
                   persist_settings=lambda s: None, pull_action=pull_action)
    qtbot.addWidget(w)
    return w


def test_pull_btn_dispatches_all_selected(qtbot, monkeypatch):
    captured = []

    def pull_action(roms, on_conflict):
        captured.append(list(roms))
        return {"written": 0, "skipped": 0, "kept": 0, "failed": 0, "missing": 0}

    w = _make_main_window(qtbot, monkeypatch, pull_action)
    a, b, c = _rom("Sonic", "genesis"), _rom("Mario", "nes"), _rom("Zelda", "nes")
    w.library.set_roms([a, b, c])
    for check, rom in w.library._checks.values():
        if rom.name in ("Sonic", "Zelda"):
            check.setChecked(True)
    w.pull_btn.click()
    assert len(captured) == 1
    assert sorted(r.name for r in captured[0]) == ["Sonic", "Zelda"]


def test_pull_btn_noop_when_nothing_selected(qtbot, monkeypatch):
    captured = []
    w = _make_main_window(qtbot, monkeypatch,
                          lambda roms, oc: captured.append(list(roms)) or {})
    w.library.set_roms([_rom("Sonic", "genesis")])
    w.pull_btn.click()
    assert captured == []


def test_pull_btn_view_parity(qtbot, monkeypatch):
    w = _make_main_window(qtbot, monkeypatch, lambda roms, oc: {})
    w.show_settings()
    assert w.pull_btn.isHidden()
    w.show_activity_log()
    assert w.pull_btn.isHidden()
    w.show_library()
    assert not w.pull_btn.isHidden()
