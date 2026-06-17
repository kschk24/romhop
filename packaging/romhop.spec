# packaging/romhop.spec  — build from repo root: pyinstaller packaging/romhop.spec
# Produces dist/romhop/ (onedir). Single exe serves both frontends: bare launch
# -> GUI, any args -> Typer CLI (see romhop.frozen_dispatch / entry.py). Built
# console=False so double-click never flashes a terminal; CLI mode re-attaches
# the parent console on Windows. PySide6's bundled PyInstaller hook collects the
# Qt platform plugins (qxcb/qoffscreen/qwindows) automatically; the --smoke-exit
# CI gate catches any that are missed.
import os

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files(
    "romhop.gui",
    includes=["assets/*", "themes/*", "themes/**/*"],
)

a = Analysis(
    ["entry.py"],
    pathex=["../src"],
    binaries=[],
    datas=datas,
    hiddenimports=["romhop.gui.app", "romhop.cli"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
# Drop the bundled libxkbcommon: it must match the host's XKB keymap data (under
# /usr/share/X11/xkb). A copy collected from the build host cannot build a valid
# xkb_state on a foreign distro, so xkb_state_key_get_layout dereferences garbage
# and SIGSEGVs on the first keypress reaching a window/dialog (see TASK-025).
# Excluding it lets the loader use the system lib (.so.0 ABI is stable) — the
# standard Qt-on-Linux approach. No-op on Windows, which ships neither.
a.binaries = [
    b for b in a.binaries
    if not os.path.basename(b[0]).startswith("libxkbcommon")
]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="romhop",          # must match install_bootstrap.LAUNCHER_NAME
    console=False,          # no terminal window on Windows
    icon="../src/romhop/gui/assets/romhop.ico",
)
coll = COLLECT(exe, a.binaries, a.datas, name="romhop")
