# Canon PIXMA iP2700 di Linux: fix margin atas & printer macet

Setup untuk Canon iP2700 (USB `04a9:10d3`) dengan CUPS + Gutenprint 5.3.4
(Ubuntu 24.04 / Linux Mint). Dites 2026-10-21.

## Masalah

1. **Posisi vertikal meleset.** Kiri–kanan akurat, tapi semua isi halaman turun
   ±3,2 mm dan bagian bawah terpotong. Ubah margin di aplikasi atau di CUPS tidak
   menolong.
2. **Macet di tengah kertas.** Printer berhenti atau jalan sangat lambat di tengah
   halaman (±1 menit per lembar, normalnya 5–10 detik).

## Penyebab

### 1. Bug `top_trim` di `rastertogutenprint`

PPD Gutenprint untuk printer yang mendukung borderless memakai `ImageableArea`
satu halaman penuh (`0 0 595 842` untuk A4), jadi CUPS mengirim raster satu halaman
penuh. Filter `rastertogutenprint` lalu memotongnya ke area yang bisa dicetak printer
(iP2700: kiri/kanan 10 pt, atas 9 pt, bawah 15 pt):

- `left_trim` dihitung **dan** dibuang tiap baris (`throwaway_data`), sehingga
  posisi horizontal benar.
- `top_trim` (9 pt = 75 baris @600 dpi) dihitung, tetapi **tidak pernah dibuang**.
  Baris 0 raster (tepi kertas) dicetak di baris pertama area cetak, yang sebenarnya
  berada 3,2 mm di bawah tepi. Akibatnya seluruh isi turun 3,2 mm dan 75 baris
  terakhir terbuang.

Yang **tidak** berhasil: mengubah `ImageableArea` di PPD. Filter selalu menganggap
raster satu halaman penuh, sehingga gambar jadi miring/terskala (±1,6%).

Queue dengan `StpiShrinkOutput=Shrink` memperkecil halaman ±97%, jadi error-nya
bertambah besar ke arah bawah. Pakai `Crop` (default di `iP2700-series`).

### 2. Mode USB dua arah

CUPS punya daftar quirk `unidir` untuk banyak Canon seri yang sama (iP4200, iP4300,
MP250, MP2xx…) karena dalam mode dua arah printer bisa hang atau mencetak sebagian
halaman (Launchpad #1032385, #1160638). iP2700 tidak ada di daftar itu
(`/usr/share/cups/usb/org.cups.usb-quirks`). Solusinya:
`usb-unidir-default=true` di queue.

Pengolahan di komputer bukan penyebabnya: satu halaman A4 cuma butuh ±2 detik.

## Fix

`top-trim.patch` membuang `top_trim` baris di awal halaman pada `Image_get_row()`,
sama seperti yang sudah dilakukan untuk margin kiri. Filter hasil build dipasang
dengan nama terpisah, **`rastertogutenprint-topfix.5.3`**, supaya tidak tertimpa
saat paket `printer-driver-gutenprint` di-update. Baris `*cupsFilter` di PPD queue
diarahkan ke filter itu.

Diverifikasi tanpa mencetak (raster di-render lalu perintah Canon `ESC (F` di-decode):
garis 4 / 10 / 15 / 20 / 25 cm dari atas jatuh tepat di 4,00 / 9,99 / 14,99 /
19,99 / 24,99 cm. Sebelum fix, semuanya +0,32 cm.

## Isi folder

| File | Fungsi |
|---|---|
| `top-trim.patch` | Patch untuk `src/cups/rastertogutenprint.c` (Gutenprint 5.3.4) |
| `build.sh` | Download source Gutenprint distro, pasang patch, build filter (tanpa root) |
| `rastertogutenprint-topfix.5.3` | Binary hasil build (Gutenprint 5.3.4, Ubuntu noble, x86_64) |
| `install.sh` | Pasang filter (sudo), arahkan queue ke filter, aktifkan USB satu arah |
| `restore.sh` | Kembalikan PPD asli dari `backup/`, hapus filter |
| `backup/` | PPD asli tiap queue sebelum diubah |
| `test-ukur-A4.pdf` | Halaman uji untuk diukur dengan penggaris |
| `test-ukur.ps` | Sumber PDF di atas |

## Setup ulang setelah install ulang Linux

```sh
# 1. Driver
sudo apt install printer-driver-gutenprint

# 2. Tambahkan printer lewat Settings/system-config-printer, pilih driver
#    "Canon iP2700 series - CUPS+Gutenprint". Cukup SATU queue, ukuran kertas A4.

# 3. Kalau versi Gutenprint / distro berbeda dari di atas, build ulang filternya
#    (butuh deb-src aktif, gcc, make, patch):
./build.sh

# 4. Pasang (otomatis menemukan semua queue iP2700, atau sebut namanya)
./install.sh            # atau: ./install.sh iP2700-series

# 5. Cetak halaman uji, skala 100%
lp -d iP2700-series -o print-scaling=none test-ukur-A4.pdf
```

Binary di folder ini cuma cocok untuk `libgutenprint.so.9` versi 5.3.4. Kalau
`apt-get source gutenprint` memberi versi yang lebih baru, cek dulu apakah patch
masih masuk dan apakah bug-nya sudah diperbaiki upstream: lihat ada tidaknya
`top_trim` di dalam `Image_get_row()` di `rastertogutenprint.c`.

## Cek dan debug

```sh
# Filter yang dipakai queue
curl -s http://localhost:631/printers/iP2700-series.ppd | grep cupsFilter
# Mode USB satu arah
curl -s http://localhost:631/printers/iP2700-series.ppd | grep usb-unidir

# Render tanpa mencetak (untuk mengecek posisi)
curl -s http://localhost:631/printers/iP2700-series.ppd > q.ppd
cupsfilter -p q.ppd -m application/vnd.cups-raster in.pdf > r.ras
PPD=q.ppd /usr/lib/cups/filter/rastertogutenprint-topfix.5.3 1 u t 1 "" r.ras > out.prn
# Log harus berisi: "Tossing top 75 rows"
```

Format output: perintah XML Canon, lalu `ESC ( p` (area cetak, unit 600 dpi), lalu
data raster di blok `ESC ( F` (8 baris per blok, 4 channel KCMY, PackBits, tiap
baris diakhiri `0x80`).
