#!/bin/sh
# Pasang semua perbaikan Canon iP2700 (Gutenprint) ke queue CUPS:
#   1. filter rastertogutenprint-topfix.5.3  (margin atas tepat)
#   2. mode USB satu arah                      (tidak macet di tengah halaman)
#   3. profil warna Canon-matched              (hijau tidak "lumut", Plain + Standard)
# Aman dijalankan berulang. PPD asli tiap queue disimpan di backup/ sekali saja.
#
# Pakai:  ./install.sh [--dry-run] [queue ...]
#         tanpa nama queue = semua queue yang driver-nya Gutenprint bjc-iP2700
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
FILTER=rastertogutenprint-topfix.5.3
FILTER_DST=/usr/lib/cups/filter/$FILTER
ICC_SRC="$HERE/color/canon-ip2700-plain.icc"
ICC_DST=/usr/share/color/icc/canon-ip2700-plain.icc
ICC_KEY='RGB.Plain.601x600dpi'

DRY=0
[ "$1" = "--dry-run" ] && { DRY=1; shift; }
run() { if [ $DRY = 1 ]; then echo "[dry-run] $*"; else "$@"; fi; }

[ -x "$HERE/$FILTER" ] || { echo "Belum ada $FILTER, jalankan ./build.sh dulu"; exit 1; }

# file sistem: hanya disalin kalau belum sama (sudo hanya diminta bila perlu)
cmp -s "$HERE/$FILTER" "$FILTER_DST" || run sudo install -o root -g root -m 755 "$HERE/$FILTER" "$FILTER_DST"
cmp -s "$ICC_SRC" "$ICC_DST" || run sudo install -o root -g root -m 644 "$ICC_SRC" "$ICC_DST"

QUEUES="$*"
if [ -z "$QUEUES" ]; then
  for q in $(lpstat -e); do
    curl -s "http://localhost:631/printers/$q.ppd" | grep -q 'StpDriverName:.*bjc-iP2700' && QUEUES="$QUEUES $q"
  done
fi
[ -n "$QUEUES" ] || { echo "Tidak ada queue iP2700. Tambahkan printer dulu (driver Gutenprint)."; exit 1; }

mkdir -p "$HERE/backup"
TMP="$(mktemp)"; trap 'rm -f "$TMP" "$TMP.new"' EXIT
for q in $QUEUES; do
  curl -s "http://localhost:631/printers/$q.ppd" > "$TMP"
  # simpan PPD asli hanya kalau belum pernah diubah oleh script ini
  if ! grep -q "$FILTER\|cupsICCProfile $ICC_KEY/" "$TMP" && [ ! -f "$HERE/backup/$q.ppd" ]; then
    run cp "$TMP" "$HERE/backup/$q.ppd"
  fi
  sed 's|rastertogutenprint\.5\.3"|'"$FILTER"'"|' "$TMP" |
    grep -v "^\*cupsICCProfile $ICC_KEY/" |
    awk -v icc="$ICC_DST" -v key="$ICC_KEY" '/^\*OpenUI \*PageSize/ && !done {
        print "*cupsICCProfile " key "/Canon-matched: \"" icc "\""; done=1 }
      { print }' > "$TMP.new"
  if [ $DRY = 1 ]; then
    echo "[dry-run] $q: perubahan PPD:"; diff "$TMP" "$TMP.new" || true
  fi
  run lpadmin -p "$q" -P "$TMP.new" -o usb-unidir-default=true
  echo "$q: filter margin + USB satu arah + profil warna aktif"
done
