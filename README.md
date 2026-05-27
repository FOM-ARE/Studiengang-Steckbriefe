# FOM Studiengang-Steckbriefe – Version 5

Standalone-Webanwendung zur Darstellung von Studiengang-Steckbriefen mit Live-Daten aus dem DWH.

## Schnellstart

**Doppelklick auf `start_app.bat`** – startet Backend + Frontend und öffnet den Browser.

Alternativ manuell:

```bash
# 1. Backend starten
cd backend
pip install -r requirements.txt
python app.py

# 2. Frontend starten (neues Terminal)
python -m http.server 8000

# 3. Browser öffnen: http://localhost:8000
```

## Voraussetzungen

- Python 3.8+
- Netzwerkzugang zu `ms-sql-107.bcw-intern.local` (Windows-Auth)
- Pakete: `flask`, `flask-cors`, `pyodbc`, `apscheduler`

## Projektstruktur

```
Studiengang_Steckbriefe_Version_5/
├── index.html          ← Frontend (Single-Page-App)
├── start_app.bat       ← Ein-Klick-Starter
├── backend/
│   ├── app.py          ← Flask-API (Port 5000)
│   └── requirements.txt
├── assets/images/      ← Bilder
└── docs/               ← Dokumentation
```

## Ports

| Dienst   | URL                    |
|----------|------------------------|
| Frontend | http://localhost:8000   |
| Backend  | http://localhost:5000   |

## Stand

Erstellt am 22.04.2026 aus Version 4 mit allen PDF-Export-Optimierungen.
