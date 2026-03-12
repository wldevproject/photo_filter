# Photo Sorter (Electron Desktop)

Aplikasi desktop untuk sortir foto cepat ke 3 kategori:

- `Bagus` (`1`)
- `Lumayan` (`2`)
- `Jelek` (`3`)

File hanya dipindahkan folder, tidak mengubah kualitas.

## Fitur

- Desktop app berbasis Electron (Windows/macOS/Linux).
- UI card modern dengan rounded corner.
- Tombol `Open Folder` (app bisa dibuka dulu tanpa load folder).
- Shortcut keyboard cepat (`1/2/3`, `0`, panah kiri/kanan, `U`, `Q`).
- Counter kategori tetap terbaca dari folder existing saat app dibuka ulang.
- Theme toggle light/dark.
- Build output: installer dan portable.
- Bundle production dalam `asar` (lebih sulit diutak-atik user awam).

## Jalankan Dev

```bash
npm install
npm run dev
```

## Build Rilis Windows

```bash
npm run dist
```

Output ada di folder `release/`:

- `NSIS Installer (.exe)`
- `Portable (.exe)`

## Build Rilis macOS / Linux

```bash
npm run dist:mac
npm run dist:linux
```

Build semua target sekaligus:

```bash
npm run dist:all
```

Catatan: Build idealnya dijalankan di OS target masing-masing (Windows build di Windows, macOS di macOS, Linux di Linux).

## Hardening Rilis (Rekomendasi)

Untuk mengurangi false-positive antivirus:

1. Gunakan code-signing certificate.
2. Build dari environment bersih.
3. Scan hasil build ke VirusTotal sebelum distribusi.
4. Jangan pakai packer/obfuscator agresif.

## Struktur Utama

- `electron/main.js`: proses utama, file operations, IPC.
- `electron/preload.js`: API aman untuk renderer.
- `electron/renderer/*`: UI/UX.
- `assets/app_icon.ico`: icon aplikasi Windows.

## Catatan

Versi Python lama masih ada di file `photo_sorter.py` sebagai referensi.

## RAW Preview (DNG/NEF Dll)

Electron tidak decode RAW secara native. App ini ambil thumbnail embedded RAW via `exiftool`.

Sumber `exiftool` yang didukung (urutan prioritas):

1. Env `EXIFTOOL_PATH`
2. Bundled binary di `assets/tools/<platform>/...` (otomatis ikut build ke `resources/tools`)
3. Binary di PATH sistem (`exiftool`)

Contoh install di Windows (PowerShell):

```powershell
winget install OliverBetz.ExifTool
```

Atau bundle binary per OS (disarankan untuk distribusi app):

- `assets/tools/win32/exiftool.exe`
- `assets/tools/darwin/exiftool`
- `assets/tools/linux/exiftool`

Detail folder ada di `assets/tools/README.md`.

Jika `exiftool` belum ada, file RAW tetap bisa disortir, hanya preview yang tampil sebagai placeholder.

Jika notifikasi "Preview RAW butuh exiftool" masih muncul:

- Restart app setelah install (agar PATH baru terbaca).
- Pastikan command `exiftool -ver` bisa jalan di terminal.
- Jika pakai paket ZIP resmi Windows, rename `exiftool(-k).exe` jadi `exiftool.exe` atau set env `EXIFTOOL_PATH` ke path executable-nya.
