from __future__ import annotations

"""Register/unregister romhop to auto-launch (to tray) at login.

Qt-free, stdlib only — mirrors ``launcher_install.py``. The OS is the source of
truth for whether autostart is on; the settings checkbox just drives
``set_enabled``. Per-OS:

- Linux: an XDG ``~/.config/autostart/romhop.desktop`` entry.
- Windows: an ``HKCU\\...\\Run`` registry value.

The autostart command launches the GUI with ``--tray`` so it starts hidden in
the system tray instead of popping a window open at boot.
"""

import os
import sys
from pathlib import Path

from romhop.gui.launcher_install import APP_NAME, COMMENT, launcher_path

TRAY_FLAG = "--tray"
RUN_VALUE_NAME = APP_NAME  # registry value / desktop basename anchor
_WIN_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def launch_command() -> list[str]:
    """The command autostart should run: the launcher plus ``--tray``.

    A frozen build is its own executable (``sys.executable``); a pip install
    shells the generated ``romhop-gui`` script.
    """
    if getattr(sys, "frozen", False):
        target = sys.executable
    else:
        target = str(launcher_path())
    return [target, TRAY_FLAG]


# --- Linux (XDG autostart) ----------------------------------------------


def _config_home(home: Path) -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME")
    return Path(xdg) if xdg else home / ".config"


def linux_autostart_path(home: Path | None = None) -> Path:
    home = home or Path.home()
    return _config_home(home) / "autostart" / "romhop.desktop"


def _autostart_desktop_text(exec_line: str) -> str:
    return (
        "[Desktop Entry]\n"
        f"Name={APP_NAME}\n"
        f"Comment={COMMENT}\n"
        f"Exec={exec_line}\n"
        "Icon=romhop\n"
        "Terminal=false\n"
        "Type=Application\n"
        "X-GNOME-Autostart-enabled=true\n"
    )


def enable_linux(home: Path | None = None) -> Path:
    home = home or Path.home()
    path = linux_autostart_path(home)
    path.parent.mkdir(parents=True, exist_ok=True)
    exec_line = " ".join(launch_command())
    path.write_text(_autostart_desktop_text(exec_line), encoding="utf-8")
    return path


def disable_linux(home: Path | None = None) -> None:
    home = home or Path.home()
    path = linux_autostart_path(home)
    if path.exists():
        path.unlink()


def is_enabled_linux(home: Path | None = None) -> bool:
    return linux_autostart_path(home).exists()


# --- Windows (registry Run key) -----------------------------------------


def enable_windows() -> None:
    import winreg

    value = " ".join(_quote_win(part) for part in launch_command())
    with winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, RUN_VALUE_NAME, 0, winreg.REG_SZ, value)


def disable_windows() -> None:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, winreg.KEY_SET_VALUE
        ) as key:
            winreg.DeleteValue(key, RUN_VALUE_NAME)
    except FileNotFoundError:
        pass  # value already absent — disabling is idempotent


def is_enabled_windows() -> bool:
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _WIN_RUN_KEY, 0, winreg.KEY_QUERY_VALUE
        ) as key:
            winreg.QueryValueEx(key, RUN_VALUE_NAME)
        return True
    except FileNotFoundError:
        return False


def _quote_win(part: str) -> str:
    return f'"{part}"' if " " in part else part


# --- dispatch ------------------------------------------------------------


def is_enabled(home: Path | None = None) -> bool:
    if os.name == "nt":
        return is_enabled_windows()
    return is_enabled_linux(home)


def set_enabled(value: bool, home: Path | None = None) -> None:
    if os.name == "nt":
        enable_windows() if value else disable_windows()
        return
    if value:
        enable_linux(home)
    else:
        disable_linux(home)
