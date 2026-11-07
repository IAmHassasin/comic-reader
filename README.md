# FolderVault

Windows desktop library manager for comic / image folders (Python 3.11 + PySide6).
Browse, filter, label and favorite folders; reading opens in **Windows Photos**.
FolderVault never writes inside your library folders. All app data lives in
`%LOCALAPPDATA%\FolderVault\`.

Design and specs: [docs/](docs/README.md).

## Run from source

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m foldervault
```

## Test and lint

```powershell
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m pytest -q
```

## Build the Windows app

```powershell
.\scripts\build.ps1
```

This script runs lint and tests, generates the icon, and runs PyInstaller (one-folder build).
Output: `dist\FolderVault\FolderVault.exe`. Copy the whole `dist\FolderVault` folder. No Python
install is needed on the target machine.

## Metadata from your own script

Album cards can show Title / Series / Type / Language / extra fields. FolderVault doesn't guess
these values: an external script writes a JSON file, and FolderVault imports it.

```powershell
# 1. Get the list of known folders (after the root has been opened once in the app)
FolderVault.exe export-meta folders.json            # or: python -m foldervault export-meta ...
# 2. Fill title/series/type/language/labels/extra in the file with your script
# 3. Preview, then import
FolderVault.exe import-meta folders.json --dry-run
FolderVault.exe import-meta folders.json
```

The format is described in [docs/03 §S6](docs/03-screens-and-interactions.md). The same import
is available in the app under **⋯ › Import metadata…**, with a preview before applying.
