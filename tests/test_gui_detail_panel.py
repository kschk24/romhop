from romhop.gui.detail_panel import DetailPanel
from romhop.romm_client import Rom, RomDetail


def _rom(rom_id=1, name="Sonic"):
    return Rom(id=rom_id, name=name, platform_slug="genesis",
               fs_name=f"{name}.md", fs_name_no_ext=name, file_names=[f"{name}.md"])


def test_set_rom_shows_local_fields_immediately(qtbot):
    panel = DetailPanel(detail_provider=lambda rom: RomDetail())
    qtbot.addWidget(panel)
    panel.set_rom(_rom(name="Sonic"))
    assert "Sonic" in panel._name_label.text()


def test_detail_fields_fill_in_after_fetch(qtbot):
    detail = RomDetail(summary="Fast.", release_date="1991",
                       genres=["Platform"], file_size=524288)
    panel = DetailPanel(detail_provider=lambda rom: detail)
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel._detail_loaded, timeout=2000):
        panel.set_rom(_rom())
    assert "Fast." in panel._summary_label.text()
    assert "1991" in panel._meta_label.text()
    assert "Platform" in panel._meta_label.text()


def test_buttons_emit_action_signals(qtbot):
    panel = DetailPanel(detail_provider=lambda rom: RomDetail())
    qtbot.addWidget(panel)
    rom = _rom()
    panel.set_rom(rom)
    got = []
    panel.pull_requested.connect(lambda r: got.append(("pull", r.id)))
    panel._pull_btn.click()
    assert got == [("pull", rom.id)]


def test_open_folder_disabled_until_downloaded(qtbot):
    panel = DetailPanel(detail_provider=lambda rom: RomDetail())
    qtbot.addWidget(panel)
    rom = _rom(rom_id=5)
    panel.set_rom(rom)
    assert not panel._folder_btn.isEnabled()
    panel.set_downloaded({5})
    panel.set_rom(rom)
    assert panel._folder_btn.isEnabled()


def test_fetch_failure_shows_error_note(qtbot):
    def boom(rom):
        raise RuntimeError("no network")

    panel = DetailPanel(detail_provider=boom)
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel._detail_loaded, timeout=2000):
        panel.set_rom(_rom())
    assert "Couldn't load details" in panel._summary_label.text()


def test_cache_hit_skips_second_fetch(qtbot):
    calls = []

    def provider(rom):
        calls.append(rom.id)
        return RomDetail(summary="Cached")

    panel = DetailPanel(detail_provider=provider)
    qtbot.addWidget(panel)
    rom = _rom()
    with qtbot.waitSignal(panel._detail_loaded, timeout=2000):
        panel.set_rom(rom)
    # Second call must use cache, not re-invoke provider.
    panel.set_rom(rom)
    assert len(calls) == 1
