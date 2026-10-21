#!/bin/sh
# Pasang filter Gutenprint yang sudah ditambal (margin atas) untuk Canon iP2700,
# lalu arahkan queue CUPS ke filter itu dan nyalakan mode USB satu arah.
# Pakai: ./install.sh [nama-queue ...]   (default: semua queue yang PPD-nya bjc-iP2700-series)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
FILTER=rastertogutenprint-topfix.5.3

[ -x "$HERE/$FILTER" ] || { echo "Belum ada $FILTER, jalankan build.sh dulu"; exit 1; }
sudo install -o root -g root -m 755 "$HERE/$FILTER" /usr/lib/cups/filter/

QUEUES="$*"
if [ -z "$QUEUES" ]; then
  for q in $(lpstat -e); do
    curl -s "http://localhost:631/printers/$q.ppd" | grep -q 'StpDriverName:.*bjc-iP2700' && QUEUES="$QUEUES $q"
  done
fi
[ -n "$QUEUES" ] || { echo "Tidak ada queue iP2700. Tambahkan printer dulu (driver Gutenprint)."; exit 1; }

mkdir -p "$HERE/backup"
TMP="$(mktemp)"
for q in $QUEUES; do
  curl -s "http://localhost:631/printers/$q.ppd" > "$TMP"
  grep -q "$FILTER" "$TMP" || cp "$TMP" "$HERE/backup/$q.ppd"
  sed 's|rastertogutenprint\.5\.3"|'"$FILTER"'"|' "$TMP" > "$TMP.new"
  lpadmin -p "$q" -P "$TMP.new" -o usb-unidir-default=true
  echo "$q: filter tambalan + USB satu arah aktif"
done
rm -f "$TMP" "$TMP.new"
