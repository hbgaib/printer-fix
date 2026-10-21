# Canon PIXMA iP2700 di Linux: margin, macet, dan warna

Perbaikan untuk Canon iP2700 (USB `04a9:10d3`) dengan CUPS + Gutenprint 5.3.4
(Ubuntu 24.04 / Linux Mint). Dites 2026-10-21/22. Hasil cetak sudah diverifikasi:
margin tepat dan warna sama dengan cetakan Windows.

| Masalah | Penyebab | Perbaikan |
|---|---|---|
| Isi halaman turun ±3,2 mm, bawah terpotong | Bug `top_trim` di `rastertogutenprint` | Filter yang sudah ditambal |
| Macet / sangat lambat di tengah halaman | Mode USB dua arah (iP2700 tidak ada di daftar quirk CUPS) | `usb-unidir-default=true` |
| Hijau terlihat "lumut", biru keunguan | Konversi warna Gutenprint memberi magenta berlebih | Profil ICC "Canon-matched" |

## Pakai

```sh
./install.sh              # pasang semua ke semua queue iP2700 (sudo hanya untuk copy file sistem)
./install.sh --dry-run    # lihat dulu apa yang akan berubah
./revert.sh               # kembali ke Gutenprint asli (PPD dari backup/)
./revert.sh --dry-run
```

`install.sh` aman dijalankan berulang. PPD asli tiap queue disimpan di `backup/`
satu kali saja, sebelum diubah.

Cetak dengan skala 100% (jangan fit to page). Profil warna hanya aktif untuk
**Plain Paper + kualitas Standard** (default). Mode lain memakai warna Gutenprint
biasa.

## Setup ulang setelah install ulang Linux

```sh
sudo apt install printer-driver-gutenprint
# Tambahkan printer (Settings / system-config-printer), driver
# "Canon iP2700 series - CUPS+Gutenprint", kertas A4. Cukup SATU queue.

./build.sh        # hanya kalau versi Gutenprint/distro berbeda (lihat di bawah)
./install.sh
lp -d iP2700-series -o print-scaling=none tests/test-ukur-A4.pdf
lp -d iP2700-series tests/test-warna-A4.pdf
```

Binary `rastertogutenprint-topfix.5.3` dibuat untuk `libgutenprint.so.9` 5.3.4
(Ubuntu noble, x86_64). Kalau versinya lain, `build.sh` mengambil source dari
repo distro (butuh `deb-src`, gcc, make, patch), memasang `top-trim.patch`, dan
mem-build tanpa root. Cek dulu apakah upstream sudah memperbaiki bug-nya: ada
tidaknya `top_trim` di dalam `Image_get_row()` di `src/cups/rastertogutenprint.c`.

Profil warna diukur pada Gutenprint 5.3.4. Kalau Gutenprint berubah versi,
ukur ulang (lihat bagian Warna).

## Isi folder

| Path | Isi |
|---|---|
| `install.sh` / `revert.sh` | Pasang / lepas semua perbaikan |
| `build.sh`, `top-trim.patch` | Build ulang filter dari source distro |
| `rastertogutenprint-topfix.5.3` | Filter hasil build |
| `color/canon-ip2700-plain.icc` | Profil warna |
| `color/build_profile.py` | Pembuat profil dari data ukur |
| `color/grid_gp.json`, `color/grid_cn.json` | Tinta 729 warna: Gutenprint / driver Canon |
| `color/mkgrid.py`, `color/measure2.py`, `color/grid-729.pdf` | Alat ukur ulang |
| `tests/test-ukur-A4.pdf` (+ `.ps`) | Garis 4/10/15/20/25 cm + penggaris mm |
| `tests/test-warna-A4.pdf` | Logo, 12 warna, spektrum, abu-abu, teks hitam |
| `backup/` | PPD asli tiap queue |

File sistem yang dipasang: `/usr/lib/cups/filter/rastertogutenprint-topfix.5.3`
dan `/usr/share/color/icc/canon-ip2700-plain.icc`. Di PPD queue:
`*cupsFilter` diarahkan ke filter topfix, plus satu baris
`*cupsICCProfile RGB.Plain.601x600dpi/Canon-matched: "…icc"`.

---

## Detail teknis

### 1. Margin atas: bug `top_trim`

PPD Gutenprint untuk printer yang mendukung borderless memakai `ImageableArea`
satu halaman penuh (`0 0 595 842` untuk A4), jadi CUPS mengirim raster satu halaman
penuh. `rastertogutenprint` memotongnya ke area cetak printer (iP2700: kiri/kanan
10 pt, atas 9 pt, bawah 15 pt):

- `left_trim` dihitung **dan** dibuang tiap baris, sehingga posisi horizontal benar.
- `top_trim` (9 pt = 75 baris @600 dpi) dihitung, tetapi **tidak pernah dibuang**.
  Akibatnya isi halaman turun 3,2 mm dan 75 baris terakhir hilang.

`top-trim.patch` membuang baris-baris itu di awal halaman pada `Image_get_row()`.

Mengubah `ImageableArea` di PPD **tidak** bisa: filter selalu menganggap raster
satu halaman penuh, jadi gambar ikut miring/terskala (±1,6%). Queue dengan
`StpiShrinkOutput=Shrink` memperkecil halaman ±97%. Pakai `Crop` (default).

Verifikasi offline: garis 4/10/15/20/25 cm jatuh di 4,00/9,99/14,99/19,99/24,99 cm
(sebelumnya semua +0,32 cm). Di kertas: tepat.

### 2. Macet: mode USB satu arah

CUPS punya quirk `unidir` untuk banyak Canon seri yang sama (iP4200, iP4300, MP250,
MP2xx…), karena dalam mode dua arah printer bisa hang atau mencetak sebagian
halaman (Launchpad #1032385, #1160638). iP2700 tidak ada di
`/usr/share/cups/usb/org.cups.usb-quirks`. Pengolahan di komputer bukan
penyebabnya: satu halaman A4 cuma butuh ±2 detik.

### 3. Warna: profil "Canon-matched"

**Acuan: driver resmi Canon dijalankan offline.** `cifip2700` dari
`cnijfilter-ip2700series 3.30` (i386) bisa jalan tanpa install:

1. Ekstrak `.deb`-nya.
2. Ganti string `/usr/lib/bjlib` di binary dengan `bjlib/////////` (panjang sama,
   relatif ke cwd), lalu salin `usr/lib/bjlib/*` ke `./bjlib/`.
3. Sediakan `libpng12.so.0` i386 asli (`libpng12-0_1.2.54-1ubuntu1_i386.deb`
   dari xenial). Symlink ke libpng16 tidak cukup (`PNG12_0` not found).

```sh
gs -q -dNOPAUSE -dBATCH -sDEVICE=ppmraw -r600 -sOutputFile=in.ppm in.pdf
LD_LIBRARY_PATH=lib ./cifip2700 --papersize a4 --media plain --imageres 600 in.ppm > canon.prn
```

Header mode `ESC (t` dari Canon **identik** dengan Gutenprint mode Standard, jadi
ukuran tetes sama dan level tinta mentah dari kedua driver bisa dibandingkan
langsung.

**Temuan** (level tinta mentah rata-rata per piksel, C M Y K; C/M 2-bit, Y/K 1-bit):

| Warna | Gutenprint | Canon |
|---|---|---|
| Hijau logo 135,193,35 | .35 **.12** .62 .01 | .31 **.04** .65 0 |
| Emas 192,142,0 | **.13** .30 .99 .01 | .07 .27 .77 0 |
| Biru 40,90,200 | 1.18 **.64** .06 0 | 1.60 **.36** .01 0 |
| Kuning murni | 0 0 1.0 0 | 0 0 .69 0 |
| Abu 50% | .08 .09 .04 .16 (K) | .38 .34 .15 0 (komposit) |

Yang dicoba dan tidak dipakai:

- `StpColorCorrection` Accurate / Bright / Hue / Uncorrected: tinta identik.
- `StpSaturation`: kuning naik, magenta di hijau hampir tetap; di kertas tidak
  terlihat beda.
- `ColorModel=CMYK` + ICC Ghostscript: hue benar, tapi teks hitam jadi rich black
  (C81 M70 Y34 K68). Tidak ada profil CMYK di sistem yang hitamnya K murni.
- `-dBlackVector`: semua vektor jadi hitam.
- Profil berbasis FOGRA: kurva tone Gutenprint (abu-abu 50% = ±16% K) khusus untuk
  printer ini, jadi model kertas cetak offset tidak cocok.

**Profil.** `build_profile.py` membuat profil output RGB (ICC v2, lut16, PCS Lab).
Tabel B2A memetakan Lab → sRGB → RGB', dengan RGB' = input yang membuat Gutenprint
mengeluarkan tinta seperti Canon. Caranya: grid 9×9×9 dari kedua driver,
interpolasi trilinear, coordinate descent pada grid koreksi 17³, lalu tabel B2A
41³. Warna dengan chroma < 8% **tidak dikoreksi** (transisi halus sampai 25%),
supaya abu-abu dan teks hitam tetap K murni ala Gutenprint. Ghostscript memakainya
sebagai `-sOutputICCProfile`. Qualifier `cupsICCProfile` harus persis
`ColorModel.MediaType.Resolution`, untuk queue ini `RGB.Plain.601x600dpi`.

Hasil uji ujung ke ujung (cupsfilter → gs + profil → Gutenprint → decode):

| Warna | Gutenprint asli | + profil | Canon |
|---|---|---|---|
| Hijau logo | .35 .12 .62 .01 | .28 .04 .61 0 | .31 .04 .65 0 |
| Emas | .13 .30 .99 .01 | .05 .27 .73 0 | .07 .27 .77 0 |
| Biru | 1.18 .64 .06 0 | 1.51 .35 .02 0 | 1.60 .36 .01 0 |
| Teks hitam (PDF asli) | K saja | K saja, identik | |

**Ukur ulang / buat ulang profil:**

```sh
cd color
python3 mkgrid.py 9                          # grid.ps + grid.json (grid-729.pdf = hasilnya)
# Gutenprint: cupsfilter -m application/vnd.cups-raster → rastertogutenprint → gp.prn
# Canon:      gs ppmraw 600 dpi → cifip2700 → cn.prn
python3 measure2.py gp.prn grid.json grid_gp.json 75 83   # offset Gutenprint (atas, kiri)
python3 measure2.py cn.prn grid.json grid_cn.json 0 0     # offset Canon
python3 build_profile.py grid_gp.json grid_cn.json canon-ip2700-plain.icc
```

## Debug

```sh
curl -s http://localhost:631/printers/iP2700-series.ppd | grep -E 'cupsFilter|cupsICCProfile'
lpoptions -p iP2700-series | tr ' ' '\n' | grep usb-unidir

# Render tanpa mencetak
curl -s http://localhost:631/printers/iP2700-series.ppd > q.ppd
cupsfilter -p q.ppd -m application/vnd.cups-raster in.pdf > r.ras 2> r.log   # r.log: OutputICCProfile=…
PPD=q.ppd /usr/lib/cups/filter/rastertogutenprint-topfix.5.3 1 u t 1 "" r.ras > out.prn
# stderr filter harus berisi: "Tossing top 75 rows"
```

Format output printer: perintah XML Canon, `ESC ( p` (area cetak, unit 600 dpi),
`ESC ( t` (mode), `ESC ( L` urutan channel `CMYK`, lalu blok raster `ESC ( F`
(8 baris per blok, satu blok per channel, PackBits, tiap baris diakhiri `0x80`).
Canon memakai `ESC ( e` untuk melewati blok kosong; Gutenprint mengirim semua blok.
