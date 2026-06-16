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
    """Per-user, writable directory the app installs into.

    POSIX: ``~/.local/lib/romhop`` — deliberately distinct from
    ``platformdirs.user_data_dir("romhop")`` (``~/.local/share/romhop``) so
    that installing/reinstalling never touches the user's mapping cache or other
    runtime data.

    Windows: ``%LOCALAPPDATA%/Programs/romhop`` (unchanged).
    """
    home = home or Path.home()
    if os.name == "nt":
        localappdata = os.environ.get("LOCALAPPDATA") or str(home / "AppData" / "Local")
        # Use type(home) to preserve the concrete Path subclass (avoids
        # WindowsPath instantiation errors when running tests on Linux).
        base = type(home)(localappdata) / "Programs"
    else:
        base = home / ".local" / "lib"
    return base / APP_DIRNAME


def installed_launcher(home: Path | None = None) -> Path:
    exe = f"{LAUNCHER_NAME}.exe" if os.name == "nt" else LAUNCHER_NAME
    return install_dir(home) / exe


def is_installed(home: Path | None = None) -> bool:
    return installed_launcher(home).exists()


def cli_link_path(home: Path | None = None) -> Path:
    """POSIX path to the ``romhop`` symlink that exposes the CLI on PATH.

    ``~/.local/bin`` is the XDG user-binary dir and conventionally on PATH, so a
    symlink there makes the single frozen exe invocable as ``romhop`` from a
    shell (bare -> GUI, args -> CLI; see :mod:`romhop.frozen_dispatch`).
    """
    home = home or Path.home()
    return home / ".local" / "bin" / LAUNCHER_NAME


def link_cli(home: Path | None = None) -> Path:
    """Symlink ``~/.local/bin/romhop`` -> the installed launcher. Returns the link.

    Idempotent: an existing link/file at the target is replaced. POSIX only
    (Windows exposes the CLI on PATH via the Inno installer instead).
    """
    link = cli_link_path(home)
    link.parent.mkdir(parents=True, exist_ok=True)
    if link.is_symlink() or link.exists():
        link.unlink()
    link.symlink_to(installed_launcher(home))
    return link


def unlink_cli(home: Path | None = None) -> None:
    """Remove the ``~/.local/bin/romhop`` symlink if present (no-op otherwise)."""
    link = cli_link_path(home)
    if link.is_symlink() or link.exists():
        link.unlink()


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
    shutil.copytree(src_onedir, tmp, symlinks=True)
    if dest.exists():
        shutil.rmtree(dest)
    os.replace(tmp, dest)  # atomic on the same filesystem
    return installed_launcher(home)


def remove_install(home: Path | None = None) -> bool:
    """Remove the installed app directory. Returns True if something was removed.

    Leaves user config/data untouched (those live elsewhere, e.g.
    platformdirs.user_data_dir). Safe to call while running from inside the
    install dir on Linux (open files survive unlink).
    """
    d = install_dir(home)
    if d.exists():
        shutil.rmtree(d)
        return True
    return False


def launch_installed(home: Path | None = None) -> None:
    """Replace the current process with the installed launcher (never returns)."""
    launcher = str(installed_launcher(home))
    os.execv(launcher, [launcher])
