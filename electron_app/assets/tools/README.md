# Bundled ExifTool Layout

Taruh binary exiftool per OS di folder ini supaya preview RAW (termasuk DNG/NEF) tetap tampil saat app di-build.

## Struktur yang dipakai app

- `assets/tools/win32/exiftool.exe`
- `assets/tools/win32/exiftool(-k).exe` (opsional, fallback)
- `assets/tools/darwin/exiftool`
- `assets/tools/linux/exiftool`

## Catatan

- File di `assets/tools` akan dicopy ke `resources/tools` lewat `electron-builder` (`extraResources`).
- Pada macOS/Linux, pastikan executable bit aktif (`chmod +x`).
- Prioritas deteksi runtime: `EXIFTOOL_PATH` -> bundled `resources/tools/...` -> PATH sistem.
