# packaging/romhop.spec  — build from repo root: pyinstaller packaging/romhop.spec
# Produces dist/romhop/ (onedir). PySide6's bundled PyInstaller hook collects the
# Qt platform plugins (qxcb/qoffscreen/qwindows) automatically; the --smoke-exit
# CI gate catches any that are missed.
from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files(
    "romhop.gui",
    includes=["assets/*", "themes/*", "themes/**/*"],
)

a = Analysis(
    ["entry_gui.py"],
    pathex=["../src"],
    binaries=[],
    datas=datas,
    hiddenimports=["romhop.gui.app"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter"],
    noarchive=False,
)
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
