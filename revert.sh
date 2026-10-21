#!/bin/sh
# Kembalikan queue Canon iP2700 ke kondisi sebelum install.sh:
# PPD asli dari backup/ (atau buang perubahan kalau backup tidak ada),
# mode USB dua arah, lalu hapus filter dan profil warna dari sistem.
#
# Pakai:  ./revert.sh [--dry-run] [queue ...]
#         tanpa nama queue = semua queue yang memakai filter topfix
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
FILTER=rastertogutenprint-topfix.5.3
ICC_KEY='RGB.Plain.601x600dpi'

DRY=0
[ "$1" = "--dry-run" ] && { DRY=1; shift; }
run() { if [ $DRY = 1 ]; then echo "[dry-run] $*"; else "$@"; fi; }

QUEUES="$*"
if [ -z "$QUEUES" ]; then
  for q in $(lpstat -e); do
    curl -s "http://localhost:631/printers/$q.ppd" | grep -q "$FILTER" && QUEUES="$QUEUES $q"
  done
fi

TMP="$(mktemp)"; trap 'rm -f "$TMP"' EXIT
for q in $QUEUES; do
  if [ -f "$HERE/backup/$q.ppd" ]; then
    run lpadmin -p "$q" -P "$HERE/backup/$q.ppd" -o usb-unidir-default=false
  else
    curl -s "http://localhost:631/printers/$q.ppd" |
      sed 's|'"$FILTER"'"|rastertogutenprint.5.3"|' |
      grep -v "^\*cupsICCProfile $ICC_KEY/" > "$TMP"
    run lpadmin -p "$q" -P "$TMP" -o usb-unidir-default=false
  fi
  echo "$q dikembalikan ke Gutenprint asli"
done

# file sistem dihapus hanya kalau tidak ada queue lain yang masih memakainya
for q in $(lpstat -e); do
  case " $QUEUES " in *" $q "*) continue ;; esac
  if curl -s "http://localhost:631/printers/$q.ppd" | grep -q "$FILTER"; then
    echo "Queue $q masih memakai filter, file sistem tidak dihapus."; exit 0
  fi
done
run sudo rm -f /usr/lib/cups/filter/$FILTER /usr/share/color/icc/canon-ip2700-plain.icc
