#!/bin/sh
# 使い方: sh html2pdf.sh <入力.html> <出力.pdf>
# Chromium で A4 の PDF にし、確認用に同じ名前の .png も作る。
# 日本語のファイル名を直接 URL にすると開けないことがあるので、いったん英数字の名前に写してから開く。
set -e
IN="$1"; OUT="$2"
CH=/opt/pw-browsers/chromium-1194/chrome-linux/chrome
TMP="$(mktemp -d)"
cp "$IN" "$TMP/page.html"
"$CH" --headless --no-sandbox --disable-gpu --no-pdf-header-footer --print-to-pdf="$TMP/page.pdf" "file://$TMP/page.html" 2>/dev/null
cp "$TMP/page.pdf" "$OUT"
pdftoppm -png -r 90 -singlefile "$OUT" "${OUT%.pdf}" 2>/dev/null || true
pdfinfo "$OUT" | grep Pages
rm -rf "$TMP"
