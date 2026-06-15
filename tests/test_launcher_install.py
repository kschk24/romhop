from __future__ import annotations

from pathlib import Path

from romhop.gui import launcher_install as li


def test_desktop_entry_text_has_required_keys():
    text = li.desktop_entry_text("/abs/path/romhop-gui")
    assert "Exec=/abs/path/romhop-gui" in text
    assert "Terminal=false" in text
    assert "StartupNotify=false" in text  # avoid tray/single-instance spinner hang
    assert "Type=Application" in text
    assert "Icon=romhop" in text


def test_launcher_path_uses_scripts_dir():
    p = li.launcher_path()
    assert p.name in ("romhop-gui", "romhop-gui.exe")
    assert p.is_absolute()


def test_assets_exist():
    for name in ("romhop.png", "romhop.svg", "romhop.ico"):
        assert li.asset(name).exists(), name


def test_install_linux_writes_desktop_and_icons(tmp_path):
    written = li.install_linux(home=tmp_path, exec_path="/x/romhop-gui")
    desktop = tmp_path / ".local/share/applications/romhop.desktop"
    png = tmp_path / ".local/share/icons/hicolor/256x256/apps/romhop.png"
    svg = tmp_path / ".local/share/icons/hicolor/scalable/apps/romhop.svg"
    assert desktop in written and desktop.exists()
    assert png in written and png.exists()
    assert svg in written and svg.exists()
    assert "Exec=/x/romhop-gui" in desktop.read_text()


def test_uninstall_linux_removes_what_install_wrote(tmp_path):
    li.install_linux(home=tmp_path, exec_path="/x/romhop-gui")
    removed = li.uninstall_linux(home=tmp_path)
    assert removed
    for p in removed:
        assert not p.exists()


def test_uninstall_linux_noop_when_absent(tmp_path):
    assert li.uninstall_linux(home=tmp_path) == []


def test_shortcut_ps_embeds_target_icon_lnk():
    ps = li.shortcut_ps(r"C:\env\Scripts\romhop-gui.exe", r"C:\a\romhop.ico", r"C:\sm\RomHop.lnk")
    assert r"C:\env\Scripts\romhop-gui.exe" in ps
    assert r"C:\a\romhop.ico" in ps
    assert r"C:\sm\RomHop.lnk" in ps
    assert "CreateShortcut" in ps
