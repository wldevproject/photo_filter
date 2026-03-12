# Photo Sorter

Versi Indonesia: [README.md](README.md)

Desktop app for fast photo sorting into 3 categories:

- `Bagus` (`1`)
- `Lumayan` (`2`)
- `Jelek` (`3`)

The app does not modify image quality. It only moves files into category folders.

## What This App Is For

Photo Sorter is built to speed up high-volume photo culling, especially after photo sessions/events, with a keyboard-first workflow.

## Key Features

- Fast sorting with keyboard shortcuts.
- Next/previous image navigation.
- Undo last move.
- Real-time category counters.
- Automatic category folder structure (`Bagus`, `Lumayan`, `Jelek`).
- Support for common image and RAW formats.
- Light/dark theme (Electron version).
- Desktop installer builds.

## How To Use (User Flow)

1. Open the app.
2. Select the source photo folder.
3. Preview the current photo.
4. Use shortcuts:
   - `1` move to `Bagus`
   - `2` move to `Lumayan`
   - `3` move to `Jelek`
   - `0` or `→` skip to next photo
   - `←` go to previous photo
   - `U` undo last move
   - `Q` / `Esc` quit the app
5. Sorted results are stored in category subfolders inside the source folder.

## Repository Structure

- `electron_app/`: main Electron-based app (Windows/macOS/Linux).
- `python_app/`: Python version (legacy/reference, Windows-focused EXE/MSI build).

## Run From Source

### Electron (Recommended)

```bash
cd electron_app
npm install
npm run dev
```

Build release:

```bash
cd electron_app
npm run dist:win
npm run dist:mac
npm run dist:linux
```

RAW notes for Electron:

- RAW previews use `exiftool`.
- `exiftool` source priority: `EXIFTOOL_PATH`, bundled binary, or system PATH.
- If decoder is missing, RAW files are still sortable, but preview becomes a placeholder.

### Python (Legacy)

```powershell
cd python_app
pip install -r requirements.txt
python photo_sorter.py
```

Build EXE + MSI:

```powershell
cd python_app
.\scripts\build_all.ps1 -ProductVersion 1.0.0
```

Build distribution archive (EXE + MSI + ZIP):

```powershell
cd python_app
.\scripts\package_release.ps1 -ProductVersion 1.0.0 -BuildIfMissing
```

Automated CI/CD (GitHub Actions):

- Workflow: `.github/workflows/python-app-ci-cd.yml`
- CI artifact includes `photo_sorter.exe`, `photo_sorter.msi`, and release ZIP.
- Pushing tag `vX.Y.Z` publishes EXE/MSI/ZIP assets to the matching GitHub Release.

Per-version docs:

- `electron_app/README.md`
- `python_app/README.md`
