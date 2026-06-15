from __future__ import annotations

"""Install/uninstall a native desktop launcher for the romhop GUI.

Cross-platform, Qt-free (stdlib only): it only writes files and shells out to
OS refresh tools. The actual GUI launcher binary is the ``romhop-gui`` entry
point (see ``[project.gui-scripts]`` in pyproject) which pip generates as a
no-console executable on Windows and a plain script on Linux.

Phase 2 (frozen AppImage/.exe via Briefcase) is intentionally not here — see
docs/superpowers/.
"""

import os
import shutil
import subprocess
import sys
import sysconfig
from importlib.resources import files
from pathlib import Path

APP_NAME = "RomHop"
COMMENT = "Sync your RomM library with ES-DE/RetroArch"
LAUNCHER_STEM = "romhop-gui"


def launcher_path() -> Path:
    """Absolute path to the pip-generated ``romhop-gui`` launcher.

    Written verbatim into the .desktop/.lnk so the shortcut never depends on
    the desktop session having ~/.local/bin (Linux) or Scripts (Windows) on
    PATH.
    """
    bindir = Path(sysconfig.get_path("scripts"))
    exe = f"{LAUNCHER_STEM}.exe" if os.name == "nt" else LAUNCHER_STEM
    return bindir / exe


def asset(name: str) -> Path:
    """Path to a bundled launcher asset (icon)."""
    return Path(str(files("romhop.gui") / "assets" / name))


def desktop_entry_text(exec_path: str) -> str:
    return (
        "[Desktop Entry]\n"
        f"Name={APP_NAME}\n"
        f"Comment={COMMENT}\n"
        f"Exec={exec_path}\n"
        "Icon=romhop\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=Game;Utility;\n"
        "StartupNotify=false\n"
    )


def shortcut_ps(target: str, icon: str, lnk: str) -> str:
    """PowerShell to create a Windows Start Menu .lnk via WScript.Shell."""
    return (
        "$s=(New-Object -COM WScript.Shell).CreateShortcut('" + lnk + "');"
        "$s.TargetPath='" + target + "';"
        "$s.IconLocation='" + icon + "';"
        "$s.Description='" + COMMENT + "';"
        "$s.Save()"
    )


def _run_quiet(cmd: list[str]) -> None:
    """Best-effort refresh command; ignore missing tool or failure."""
    if shutil.which(cmd[0]) is None:
        return
    try:
        subprocess.run(cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError:
        pass


# --- Linux (XDG) ---------------------------------------------------------


def _linux_paths(home: Path) -> dict[str, Path]:
    share = home / ".local" / "share"
    return {
        "desktop": share / "applications" / "romhop.desktop",
        "icon_png": share / "icons" / "hicolor" / "256x256" / "apps" / "romhop.png",
        "icon_svg": share / "icons" / "hicolor" / "scalable" / "apps" / "romhop.svg",
    }


def install_linux(home: Path | None = None, exec_path: str | None = None) -> list[Path]:
    home = home or Path.home()
    exec_path = exec_path or str(launcher_path())
    paths = _linux_paths(home)
    written: list[Path] = []

    paths["desktop"].parent.mkdir(parents=True, exist_ok=True)
    paths["desktop"].write_text(desktop_entry_text(exec_path), encoding="utf-8")
    written.append(paths["desktop"])

    for asset_name, key in (("romhop.png", "icon_png"), ("romhop.svg", "icon_svg")):
        src = asset(asset_name)
        if src.exists():
            paths[key].parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, paths[key])
            written.append(paths[key])

    _run_quiet(["update-desktop-database", str(paths["desktop"].parent)])
    _run_quiet(["gtk-update-icon-cache", str(home / ".local" / "share" / "icons" / "hicolor")])
    return written


def uninstall_linux(home: Path | None = None) -> list[Path]:
    home = home or Path.home()
    removed: list[Path] = []
    for p in _linux_paths(home).values():
        if p.exists():
            p.unlink()
            removed.append(p)
    _run_quiet(["update-desktop-database", str(_linux_paths(home)["desktop"].parent)])
    return removed


# --- Windows -------------------------------------------------------------


def _windows_lnk() -> Path:
    appdata = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / f"{APP_NAME}.lnk"


def install_windows(lnk: Path | None = None) -> list[Path]:
    lnk = lnk or _windows_lnk()
    lnk.parent.mkdir(parents=True, exist_ok=True)
    target = str(launcher_path())
    icon = str(asset("romhop.ico"))
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", shortcut_ps(target, icon, str(lnk))],
        check=True,
    )
    return [lnk]


def uninstall_windows(lnk: Path | None = None) -> list[Path]:
    lnk = lnk or _windows_lnk()
    if lnk.exists():
        lnk.unlink()
        return [lnk]
    return []


# --- dispatch ------------------------------------------------------------


def install() -> list[Path]:
    if os.name == "nt":
        return install_windows()
    return install_linux()


def uninstall() -> list[Path]:
    if os.name == "nt":
        return uninstall_windows()
    return uninstall_linux()
