# Build FolderVault as a one-folder Windows app with PyInstaller.
# Usage (from the repo root):  .\scripts\build.ps1
# Output: dist\FolderVault\FolderVault.exe
# Note: no $ErrorActionPreference = "Stop": Windows PowerShell 5.1 would treat PyInstaller's
# stderr logging as an error. Each step checks $LASTEXITCODE instead.
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Virtual env not found. Run: py -3.11 -m venv .venv; .\.venv\Scripts\python.exe -m pip install -e "".[dev]"""
}

& $python -m ruff check .
if ($LASTEXITCODE -ne 0) { throw "Lint failed" }
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed" }

$buildDir = Join-Path $root "build"
& $python scripts\make_icon.py $buildDir
if ($LASTEXITCODE -ne 0) { throw "Icon generation failed" }

& $python -m PyInstaller --noconfirm --clean --windowed `
    --name FolderVault `
    --icon (Join-Path $buildDir "app.ico") `
    --paths (Join-Path $root "src") `
    --distpath (Join-Path $root "dist") `
    --workpath (Join-Path $buildDir "pyinstaller") `
    --specpath $buildDir `
    --exclude-module tkinter `
    (Join-Path $root "src\foldervault\__main__.py")
if ($LASTEXITCODE -ne 0) { throw "PyInstaller failed" }

Write-Host "Built: $(Join-Path $root 'dist\FolderVault\FolderVault.exe')"
