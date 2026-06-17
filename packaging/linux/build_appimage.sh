#!/usr/bin/env bash
# Build the bootstrap AppImage from a prior `pyinstaller packaging/romhop.spec`.
# Requires: appimagetool on PATH. Run from repo root.
set -euo pipefail

VERSION="$(.venv/bin/python -c 'import romhop; print(romhop.__version__)')"
APPDIR="packaging/build/AppDir"

rm -rf "$APPDIR"
mkdir -p "$APPDIR/usr/bin"
cp -r packaging/dist/romhop "$APPDIR/usr/bin/romhop"

# Remove Qt imageformat plugins whose system-lib deps have changed SONAME on
# newer distros (libtiff.so.5 → .so.6 on Fedora/Arch/Ubuntu 23.04+). A failed
# dlopen can corrupt dl-state and crash unrelated subsequent plugin loads.
# romhop only uses JPEG/PNG/WebP for cover art; TIFF/JASPER are not needed.
find "$APPDIR/usr/bin/romhop" \
    -name "libqtiff.so" -o -name "libqjasper.so" \
    | xargs --no-run-if-empty rm -v
install -m 0755 packaging/linux/AppRun "$APPDIR/AppRun"
cp packaging/linux/romhop.desktop "$APPDIR/romhop.desktop"
cp src/romhop/gui/assets/romhop.png "$APPDIR/romhop.png"

mkdir -p dist
appimagetool "$APPDIR" "dist/romhop-installer-${VERSION}-x86_64.AppImage"
echo "built dist/romhop-installer-${VERSION}-x86_64.AppImage"
