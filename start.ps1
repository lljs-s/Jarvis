# Jarvis starten (Windows, PowerShell)
#
#   Rechtsklick auf diese Datei -> "Mit PowerShell ausfuehren"
#   oder im Terminal:  .\start.ps1
#
# Das Skript prueft die Einrichtung, startet Server und Oberflaeche und
# zeigt den Link an, mit dem du Jarvis im Browser oeffnest.

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

if (-not (Test-Path ".venv\Scripts\Activate.ps1")) {
    Write-Host "Die Python-Umgebung fehlt noch. Einmalig einrichten:" -ForegroundColor Yellow
    Write-Host "  python -m venv .venv"
    Write-Host "  .\.venv\Scripts\Activate.ps1"
    Write-Host '  pip install -e ".[dev]"'
    exit 1
}

if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Die Pakete der Oberflaeche fehlen noch. Einmalig einrichten:" -ForegroundColor Yellow
    Write-Host "  cd frontend"
    Write-Host "  npm install"
    Write-Host "  cd .."
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "Keine .env gefunden - ich lege sie aus der Vorlage an." -ForegroundColor Yellow
    Copy-Item .env.example .env
}

& ".venv\Scripts\python.exe" -m jarvis.cli dev
