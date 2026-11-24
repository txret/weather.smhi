#!/bin/sh
# Build an installable zip: weather.smhi-<version>.zip containing weather.smhi/
# Usage: tools/build_zip.sh [output-dir]   (default: the repository root)
set -eu

ROOT=$(cd "$(dirname "$0")/.." && pwd)
OUT=$(cd "${1:-$ROOT}" && pwd)
ID=$(sed -n 's/.*<addon id="\([^"]*\)".*/\1/p' "$ROOT/addon.xml")
VERSION=$(sed -n 's/.*<addon id="[^"]*" name="[^"]*" version="\([^"]*\)".*/\1/p' "$ROOT/addon.xml")
ZIP="$OUT/$ID-$VERSION.zip"

STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
mkdir "$STAGE/$ID"
cp -R "$ROOT/addon.xml" "$ROOT/default.py" "$ROOT/icon.png" "$ROOT/LICENSE.txt" \
      "$ROOT/README.md" "$ROOT/resources" "$STAGE/$ID/"
find "$STAGE" -name '__pycache__' -type d -prune -exec rm -rf {} +
find "$STAGE" -name '*.pyc' -delete

rm -f "$ZIP"
(cd "$STAGE" && zip -qr "$ZIP" "$ID")
echo "$ZIP"
