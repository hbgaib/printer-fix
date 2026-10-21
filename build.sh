#!/bin/sh
# Build ulang rastertogutenprint-topfix.5.3 dari source Gutenprint distro + top-trim.patch.
# Tidak butuh root: header CUPS diambil dari .deb yang diekstrak lokal.
# Syarat: deb-src aktif, gcc, make, patch.
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$(mktemp -d)"
echo "Folder kerja: $WORK"
cd "$WORK"

apt-get source --download-only gutenprint
mkdir sysroot
apt-get download libcups2-dev libcupsimage2-dev
for f in *.deb; do dpkg-deb -x "$f" sysroot; done
# link ke libcups shared milik sistem, bukan .a statis (butuh gssapi)
L=sysroot/usr/lib/x86_64-linux-gnu
rm -f $L/libcups.a $L/libcupsimage.a
ln -sf /usr/lib/x86_64-linux-gnu/libcups.so.2 $L/libcups.so
ln -sf /usr/lib/x86_64-linux-gnu/libcupsimage.so.2 $L/libcupsimage.so

tar xf gutenprint_*.orig.tar.xz
cd gutenprint-*/
patch -p1 < "$HERE/top-trim.patch"

export PATH="$WORK/sysroot/usr/bin:$PATH"
CPPFLAGS="-I$WORK/sysroot/usr/include" LDFLAGS="-L$WORK/$L" ./configure \
  --prefix=/usr --libdir=/usr/lib/x86_64-linux-gnu --sysconfdir=/etc \
  --disable-static --enable-shared --disable-rpath --with-modules=dlopen \
  --without-gimp2 --disable-libgutenprintui2 --with-cups \
  --enable-cups-level3-ppds --enable-globalized-cups-ppds --enable-cups-1_2-enhancements \
  --disable-cups-ppds --disable-test --disable-testpattern --disable-nls --without-doc >/dev/null
make -j"$(nproc)" -C include >/dev/null
make -j"$(nproc)" -C src/main >/dev/null 2>&1
make -C src/cups rastertogutenprint.5.3 >/dev/null

cp src/cups/.libs/rastertogutenprint.5.3 "$HERE/rastertogutenprint-topfix.5.3"
echo "Jadi: $HERE/rastertogutenprint-topfix.5.3"
echo "Hapus folder kerja kalau sudah: rm -rf $WORK"
