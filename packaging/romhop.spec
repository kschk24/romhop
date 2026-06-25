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
#
# Also drop Qt imageformat plugins whose system-lib deps track SONAME on the
# host distro (libtiff.so.5→.so.6 on Fedora/Arch; libqjasper similarly). A
# failed dlopen can corrupt dl-state and crash unrelated plugin loads. romhop
# only needs JPEG/PNG/WebP for cover art — TIFF/JASPER are unused.
#
# Drop Qt's AT-SPI2 accessibility plugin: it dlopen's libatspi.so.0 from the
# system; the SONAME version on Arch/Fedora differs from the Ubuntu 24.04 CI
# build, causing a segfault on QApplication init. romhop ships no screen-reader
# features so removing it is safe (see TASK-028).
_EXCLUDED_PLUGINS = {"libqtiff.so", "libqjasper.so", "libqatspiplugin.so"}
a.binaries = [
    b for b in a.binaries
    if not os.path.basename(b[0]).startswith("libxkbcommon")
    and os.path.basename(b[0]) not in _EXCLUDED_PLUGINS
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
