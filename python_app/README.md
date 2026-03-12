# Python App (Legacy)

Ini versi Python lama dari Photo Sorter. Dipertahankan sebagai referensi/fallback.

## Struktur Build

- `photo_sorter.py`: app utama.
- `assets/app_icon.ico` + `assets/app_icon.png`: icon app.
- `installer.wxs`: template MSI (WiX v4/v5/v6).
- `scripts/build_exe.ps1`: build EXE dengan PyInstaller.
- `scripts/build_msi.ps1`: build MSI dari EXE.
- `scripts/build_all.ps1`: build EXE lalu MSI.
- `requirements.txt`: dependency runtime app.
- `requirements-build.txt`: dependency tool build.

## Prasyarat

- Windows 10/11.
- Python `3.10+` (dengan `pip`).
- Modul `tkinter` (umumnya sudah ikut installer Python).
- WiX CLI modern (`wix` command).

## Menjalankan (Dev)

```powershell
cd python_app
pip install -r requirements.txt
python photo_sorter.py
```

Mode UI:

- `Dark Mode` / `Light Mode`: ganti tema.
- `Compact: On/Off`: ganti kerapatan layout (lebih rapat untuk layar kecil).

## Setup Tool Build (Sekali Saja)

```powershell
cd python_app
pip install -r requirements-build.txt
```

Jika `wix` belum ada:

```powershell
dotnet tool install --global wix
```

Lalu restart terminal dan cek:

```powershell
wix --version
```

## Build EXE

```powershell
cd python_app
.\scripts\build_exe.ps1
```

Output:

- `dist/photo_sorter.exe`

Catatan:

- Script otomatis install/upgrade dependency build.
- Untuk skip install dependency: `.\scripts\build_exe.ps1 -SkipInstallDeps`

## Build MSI

Pastikan `dist/photo_sorter.exe` sudah ada, lalu:

```powershell
cd python_app
.\scripts\build_msi.ps1
```

Output:

- `dist/photo_sorter.msi`

Contoh custom version:

```powershell
.\scripts\build_msi.ps1 -ProductVersion 1.0.1
```

Contoh build EXE otomatis jika belum ada:

```powershell
.\scripts\build_msi.ps1 -BuildExeIfMissing
```

## Build EXE + MSI Sekaligus

```powershell
cd python_app
.\scripts\build_all.ps1 -ProductVersion 1.0.1
```

## Troubleshooting

- Error `Cannot find the File file 'dist\photo_sorter.exe'`:
  - Jalankan `.\scripts\build_exe.ps1` dulu.
- Error `wix is not recognized`:
  - Install WiX CLI (`dotnet tool install --global wix`) lalu restart terminal.
- Icon tidak muncul:
  - Pastikan file `assets/app_icon.ico` dan `assets/app_icon.png` ada.

## Catatan

- Untuk distribusi lintas OS dengan installer siap pakai, gunakan versi Electron di `../electron_app`.
