#!/usr/bin/env bash
# Build the bootstrap AppImage from a prior `pyinstaller packaging/romhop.spec`.
# Requires: appimagetool on PATH. Run from repo root.
set -euo pipefail

VERSION="$(.venv/bin/python -c 'import romhop; print(romhop.__version__)')"
APPDIR="packaging/build/AppDir"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -r packaging/dist/romhop "$APPDIR/usr/bin/romhop"

install -m 0755 packaging/linux/AppRun "$APPDIR/AppRun"
cp packaging/linux/romhop.desktop "$APPDIR/romhop.desktop"
cp src/romhop/gui/assets/romhop.png "$APPDIR/romhop.png"

mkdir -p dist
appimagetool "$APPDIR" "dist/romhop-installer-${VERSION}-x86_64.AppImage"
echo "built dist/romhop-installer-${VERSION}-x86_64.AppImage"
