# Buduje samodzielny plik YouTrak.exe (folder dist\)
# Uruchom w PowerShell z katalogu projektu: .\build.ps1

$ErrorActionPreference = "Stop"

if (-not (Test-Path "venv")) {
    python -m venv venv
}

& ".\venv\Scripts\python.exe" -m pip install --upgrade pip
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt

& ".\venv\Scripts\pyinstaller.exe" `
    --noconfirm `
    --onefile `
    --windowed `
    --name "YouTrak" `
    --icon "assets\icon.ico" `
    --add-data "assets;assets" `
    --collect-all imageio_ffmpeg `
    --collect-all yt_dlp `
    app.py

Write-Host ""
Write-Host "Gotowe. Plik wykonywalny: dist\YouTrak.exe"
