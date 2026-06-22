from romhop.gui.detail_panel import DetailPanel, _strip_tags
from romhop.romm_client import Rom, RomDetail


def _rom(rom_id=1, name="Sonic", regions=None, languages=None, tags=None,
         revision=None, screenshots=None):
    return Rom(
        id=rom_id, name=name, platform_slug="genesis",
        fs_name=f"{name}.md", fs_name_no_ext=name, file_names=[f"{name}.md"],
        regions=regions or [],
        languages=languages or [],
        tags=tags or [],
        revision=revision,
        screenshots=screenshots or [],
    )


def _panel(**kw):
    return DetailPanel(**kw)


# --- unit: _strip_tags ---

def test_strip_tags_removes_parens():
    assert _strip_tags("Sonic (USA)") == "Sonic"


def test_strip_tags_multiple():
    assert _strip_tags("Sonic (USA) (Rev 1)") == "Sonic"


def test_strip_tags_no_parens():
    assert _strip_tags("Sonic") == "Sonic"


def test_strip_tags_nested_not_greedy():
    # Only strips outer balanced parens groups
    assert _strip_tags("Game (USA)") == "Game"


# --- widget tests ---

def test_set_rom_shows_stripped_title(qtbot):
    panel = _panel(detail_provider=lambda rom: RomDetail())
    qtbot.addWidget(panel)
    panel.set_rom(_rom(name="Sonic (USA) (Rev 1)"))
    assert panel._name_label.text() == "Sonic"


def test_platform_label_fn_used(qtbot):
    panel = _panel(
        detail_provider=lambda rom: RomDetail(),
        platform_label=lambda rom: "Mega Drive",
    )
    qtbot.addWidget(panel)
    panel.set_rom(_rom())
    assert panel._platform_display.text() == "Mega Drive"


def test_platform_label_fallback(qtbot):
    panel = _panel(detail_provider=lambda rom: RomDetail())
    qtbot.addWidget(panel)
    panel.set_rom(_rom())
    # falls back to platform_slug
    assert "genesis" in panel._platform_display.text()


def test_chips_region_flag(qtbot):
    panel = _panel(detail_provider=lambda rom: RomDetail())
    qtbot.addWidget(panel)
    panel.set_rom(_rom(regions=["USA"], languages=["En"]))
    chips = [
        panel._chips_layout.itemAt(i).widget()
        for i in range(panel._chips_layout.count())
    ]
    texts = [c.text() for c in chips]
    assert any("🇺🇸" in t for t in texts)
    assert any("En" in t for t in texts)


def test_chips_revision(qtbot):
    panel = _panel(detail_provider=lambda rom: RomDetail())
    qtbot.addWidget(panel)
    panel.set_rom(_rom(revision="Rev 1"))
    chips = [
        panel._chips_layout.itemAt(i).widget()
        for i in range(panel._chips_layout.count())
    ]
    assert any("Rev 1" in c.text() for c in chips)


def test_chips_cleared_on_rom_switch(qtbot):
    panel = _panel(detail_provider=lambda rom: RomDetail())
    qtbot.addWidget(panel)
    panel.set_rom(_rom(regions=["USA"]))
    panel.set_rom(_rom(rom_id=2, regions=[]))
    assert panel._chips_layout.count() == 0


def test_detail_fields_fill_in_after_fetch(qtbot):
    detail = RomDetail(summary="Fast.", release_date="1991",
                       genres=["Platform"], file_size=524288)
    panel = _panel(detail_provider=lambda rom: detail)
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel._detail_loaded, timeout=2000):
        panel.set_rom(_rom())
    assert "Fast." in panel._summary_label.text()
    assert "1991" in panel._meta_label.text()
    assert "Platform" in panel._meta_label.text()


def test_buttons_emit_action_signals(qtbot):
    panel = _panel(detail_provider=lambda rom: RomDetail())
    qtbot.addWidget(panel)
    rom = _rom()
    panel.set_rom(rom)
    got = []
    panel.pull_requested.connect(lambda r: got.append(("pull", r.id)))
    panel._pull_btn.click()
    assert got == [("pull", rom.id)]


def test_open_folder_disabled_until_downloaded(qtbot):
    panel = _panel(detail_provider=lambda rom: RomDetail())
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

    panel = _panel(detail_provider=boom)
    qtbot.addWidget(panel)
    with qtbot.waitSignal(panel._detail_loaded, timeout=2000):
        panel.set_rom(_rom())
    assert "Couldn't load details" in panel._summary_label.text()


def test_cache_hit_skips_second_fetch(qtbot):
    calls = []

    def provider(rom):
        calls.append(rom.id)
        return RomDetail(summary="Cached")

    panel = _panel(detail_provider=provider)
    qtbot.addWidget(panel)
    rom = _rom()
    with qtbot.waitSignal(panel._detail_loaded, timeout=2000):
        panel.set_rom(rom)
    # Second call must use cache, not re-invoke provider.
    panel.set_rom(rom)
    assert len(calls) == 1


def test_no_files_label(qtbot):
    panel = _panel(detail_provider=lambda rom: RomDetail())
    qtbot.addWidget(panel)
    assert not hasattr(panel, "_files_label")


def test_screenshot_wins_over_late_cover(qtbot):
    """Cover arriving after screenshot must not downgrade the image."""
    from PySide6.QtGui import QImage
    cover_img = QImage(1, 1, QImage.Format.Format_RGB32)
    cover_img.fill(0xFF0000)
    ss_img = QImage(1, 1, QImage.Format.Format_RGB32)
    ss_img.fill(0x00FF00)

    panel = DetailPanel(detail_provider=lambda r: RomDetail())
    qtbot.addWidget(panel)
    rom = _rom(screenshots=["fake.jpg"])
    panel.set_rom(rom)

    # simulate screenshot arriving first
    panel._on_image_ready(rom.id, ss_img, rom, "screenshot")
    assert panel._shown_source == "screenshot"
    pix_after_ss = panel._image_label.pixmap()

    # now cover arrives late — must be ignored
    panel._on_image_ready(rom.id, cover_img, rom, "cover")
    assert panel._shown_source == "screenshot"
    assert panel._image_label.pixmap().toImage() == pix_after_ss.toImage()


def test_cover_applied_when_no_screenshot(qtbot):
    from PySide6.QtGui import QImage
    cover_img = QImage(1, 1, QImage.Format.Format_RGB32)
    cover_img.fill(0x0000FF)

    panel = DetailPanel(detail_provider=lambda r: RomDetail())
    qtbot.addWidget(panel)
    rom = _rom()
    panel.set_rom(rom)

    panel._on_image_ready(rom.id, cover_img, rom, "cover")
    assert panel._shown_source == "cover"


def test_rom_switch_resets_shown_source(qtbot):
    panel = DetailPanel(detail_provider=lambda r: RomDetail())
    qtbot.addWidget(panel)
    rom1 = _rom(rom_id=1, screenshots=["s.jpg"])
    rom2 = _rom(rom_id=2)
    panel.set_rom(rom1)
    panel._shown_source = "screenshot"
    panel.set_rom(rom2)
    assert panel._shown_source == "none"
