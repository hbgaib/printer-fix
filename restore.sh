#!/bin/sh
# Kembalikan queue ke PPD asli (dari backup/) dan mode USB dua arah, lalu hapus filter tambalan.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
for ppd in "$HERE"/backup/*.ppd; do
  q="$(basename "$ppd" .ppd)"
  lpstat -p "$q" >/dev/null 2>&1 || continue
  lpadmin -p "$q" -P "$ppd" -o usb-unidir-default=false
  echo "$q dikembalikan"
done
sudo rm -f /usr/lib/cups/filter/rastertogutenprint-topfix.5.3
