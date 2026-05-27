@echo off
chcp 65001 >nul
title FOM Studiengang-Steckbriefe App

echo ============================================
echo   FOM Studiengang-Steckbriefe App
echo ============================================
echo.

:: Prüfe ob Python verfügbar ist
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [FEHLER] Python wurde nicht gefunden!
    echo Bitte installiere Python 3.8+ und füge es zum PATH hinzu.
    pause
    exit /b 1
)

:: Prüfe ob pip-Pakete installiert sind
echo [1/3] Prüfe Abhängigkeiten...
python -c "import flask; import flask_cors; import pyodbc; import apscheduler" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] Installiere fehlende Pakete...
    pip install flask flask-cors pyodbc apscheduler
    if %errorlevel% neq 0 (
        echo [FEHLER] Paketinstallation fehlgeschlagen!
        pause
        exit /b 1
    )
)
echo        OK - Alle Pakete vorhanden.

:: Starte Backend (Flask auf Port 5000)
echo [2/3] Starte Backend auf http://localhost:5000 ...
cd /d "%~dp0backend"
start "Flask-Backend" python app.py

:: Warte kurz bis Backend bereit ist
echo        Warte auf Backend-Start...
timeout /t 3 /nobreak >nul

:: Starte Frontend (HTTP-Server auf Port 8000)
echo [3/3] Starte Frontend auf http://localhost:8000 ...
cd /d "%~dp0"
start "Frontend-Server" python -m http.server 8000

:: Warte kurz und öffne Browser
timeout /t 2 /nobreak >nul
echo.
echo ============================================
echo   App gestartet!
echo   Frontend: http://localhost:8000
echo   Backend:  http://localhost:5000
echo ============================================
echo.
echo Öffne Browser...
start http://localhost:8000

echo.
echo Drücke eine beliebige Taste zum Beenden beider Server.
pause >nul

:: Beende die Server
echo Beende Server...
taskkill /fi "WINDOWTITLE eq Flask-Backend*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Frontend-Server*" /f >nul 2>&1
echo Server beendet.
