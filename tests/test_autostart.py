from __future__ import annotations

import os
from pathlib import Path

import pytest

from romhop.gui import autostart


# --- launch command -------------------------------------------------------


def test_launch_command_uses_launcher_path_when_not_frozen(monkeypatch):
    monkeypatch.setattr(autostart.sys, "frozen", False, raising=False)
    monkeypatch.setattr(
        autostart, "launcher_path", lambda: Path("/opt/romhop/romhop-gui")
    )
    cmd = autostart.launch_command()
    assert cmd == ["/opt/romhop/romhop-gui", autostart.TRAY_FLAG]


def test_launch_command_uses_sys_executable_when_frozen(monkeypatch):
    monkeypatch.setattr(autostart.sys, "frozen", True, raising=False)
    monkeypatch.setattr(autostart.sys, "executable", "/opt/romhop/RomHop.exe")
    cmd = autostart.launch_command()
    assert cmd == ["/opt/romhop/RomHop.exe", autostart.TRAY_FLAG]


# --- Linux (XDG autostart) ------------------------------------------------


def test_linux_autostart_path_under_config_autostart(tmp_path):
    p = autostart.linux_autostart_path(home=tmp_path)
    assert p == tmp_path / ".config" / "autostart" / "romhop.desktop"


def test_linux_autostart_path_respects_xdg_config_home(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg"))
    p = autostart.linux_autostart_path(home=tmp_path)
    assert p == tmp_path / "xdg" / "autostart" / "romhop.desktop"


def test_enable_linux_writes_autostart_entry(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(
        autostart, "launch_command", lambda: ["/opt/romhop/romhop-gui", "--tray"]
    )
    autostart.enable_linux(home=tmp_path)

    path = autostart.linux_autostart_path(home=tmp_path)
    assert path.exists()
    text = path.read_text(encoding="utf-8")
    assert "[Desktop Entry]" in text
    assert "Type=Application" in text
    assert "Exec=/opt/romhop/romhop-gui --tray" in text
    assert "X-GNOME-Autostart-enabled=true" in text
    assert autostart.is_enabled_linux(home=tmp_path) is True


def test_disable_linux_removes_entry(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(
        autostart, "launch_command", lambda: ["/opt/romhop/romhop-gui", "--tray"]
    )
    autostart.enable_linux(home=tmp_path)
    assert autostart.is_enabled_linux(home=tmp_path) is True

    autostart.disable_linux(home=tmp_path)
    assert autostart.is_enabled_linux(home=tmp_path) is False
    assert not autostart.linux_autostart_path(home=tmp_path).exists()


def test_disable_linux_is_idempotent_when_absent(tmp_path):
    # No entry written; disabling must not raise.
    autostart.disable_linux(home=tmp_path)
    assert autostart.is_enabled_linux(home=tmp_path) is False


# --- dispatch (Linux host) ------------------------------------------------


@pytest.mark.skipif(os.name == "nt", reason="POSIX dispatch")
def test_set_enabled_and_is_enabled_dispatch_linux(tmp_path, monkeypatch):
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.setattr(
        autostart, "launch_command", lambda: ["/opt/romhop/romhop-gui", "--tray"]
    )
    assert autostart.is_enabled(home=tmp_path) is False
    autostart.set_enabled(True, home=tmp_path)
    assert autostart.is_enabled(home=tmp_path) is True
    autostart.set_enabled(False, home=tmp_path)
    assert autostart.is_enabled(home=tmp_path) is False


# --- Windows (registry Run key) -------------------------------------------


@pytest.mark.skipif(os.name != "nt", reason="Windows registry only")
def test_windows_enable_disable_roundtrip(monkeypatch):
    monkeypatch.setattr(
        autostart, "launch_command", lambda: ["C:\\romhop\\RomHop.exe", "--tray"]
    )
    autostart.disable_windows()  # clean slate
    assert autostart.is_enabled_windows() is False
    autostart.enable_windows()
    assert autostart.is_enabled_windows() is True
    autostart.disable_windows()
    assert autostart.is_enabled_windows() is False
