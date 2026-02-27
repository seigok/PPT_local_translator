#!/usr/bin/env bash
set -euo pipefail

mkdir -p source
URL="https://raw.githubusercontent.com/scanny/python-pptx/master/tests/test_files/test.pptx"
OUT="source/sample_from_web.pptx"

if command -v curl >/dev/null 2>&1; then
  curl -L "$URL" -o "$OUT"
else
  wget "$URL" -O "$OUT"
fi

echo "Downloaded: $OUT"
