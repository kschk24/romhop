# src/romhop/install_bootstrap.py
from __future__ import annotations

"""Qt-free bootstrap for the frozen Linux AppImage installer.

The AppImage payload is a PyInstaller onedir bundle. On first run it copies
itself into a per-user, writable location and a desktop shortcut is installed
(see ``gui.launcher_install``), then the installed copy is launched. Subsequent
runs just launch the installed copy.

Per-user writable install is the invariant sub-project 2 (tufup auto-update)
depends on: the app must overwrite its own files without admin rights. Hence
``install_dir`` is OS-agnostic even though only Linux exercises it here.
"""

import os
import shutil
from pathlib import Path

APP_DIRNAME = "romhop"
LAUNCHER_NAME = "romhop"  # must match EXE name in packaging/romhop.spec


def install_dir(home: Path | None = None) -> Path:
    """Per-user, writable directory the app installs into."""
    home = home or Path.home()
    if os.name == "nt":
        localappdata = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        # Use type(home) to preserve the concrete Path subclass (avoids
        # WindowsPath instantiation errors when running tests on Linux).
        base = type(home)(localappdata) / "Programs"
    else:
        base = home / ".local" / "share"
    return base / APP_DIRNAME


def installed_launcher(home: Path | None = None) -> Path:
    exe = f"{LAUNCHER_NAME}.exe" if os.name == "nt" else LAUNCHER_NAME
    return install_dir(home) / exe


def is_installed(home: Path | None = None) -> bool:
    return installed_launcher(home).exists()


def extract_and_install(src_onedir: Path, home: Path | None = None) -> Path:
    """Copy the onedir bundle into the install dir, return the launcher path.

    Copies to a temp sibling then atomically renames it into place, so an
    interrupted copy never leaves a half-populated install dir.
    """
    dest = install_dir(home)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.parent / (dest.name + ".tmp")
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.copytree(src_onedir, tmp)
    if dest.exists():
        shutil.rmtree(dest)
    os.replace(tmp, dest)  # atomic on the same filesystem
    return installed_launcher(home)


def launch_installed(home: Path | None = None) -> None:
    """Replace the current process with the installed launcher (never returns)."""
    launcher = str(installed_launcher(home))
    os.execv(launcher, [launcher])
