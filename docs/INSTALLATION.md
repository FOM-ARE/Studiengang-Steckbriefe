# INSTALLATION.md - Installationsanleitung

## Voraussetzungen

- Moderner Webbrowser (Chrome, Firefox, Edge, Safari)
- Internetverbindung (für Chart.js CDN)
- Optional: Node.js oder Python (für lokalen Server)

## Installation

### Schritt 1: Dateien herunterladen/kopieren

Der Ordner `Steckbrief-App-Production` enthält alle notwendigen Dateien:
```
- index.html
- Rahmengebendes/Asgard-HO/Allgemeines/Fom Logo.jpg
- README.md (diese Datei)
```

### Schritt 2: App öffnen

#### Variante A: Direkt im Browser (einfachste Methode)
1. Navigiere zu: `Z:\12_Hochschulinformationen bereitstellen\Studiengang-Steckbrief\Steckbrief-App-Production\`
2. Doppelklick auf `index.html`
3. oder Rechtsklick → `Öffnen mit` → Browser auswählen

#### Variante B: Mit lokalem Server (Python)
```bash
cd "Z:\12_Hochschulinformationen bereitstellen\Studiengang-Steckbrief\Steckbrief-App-Production"
python -m http.server 8000
```
Dann öffne: `http://localhost:8000/`

#### Variante C: Mit lokalem Server (Node.js)
```bash
cd "Z:\12_Hochschulinformationen bereitstellen\Studiengang-Steckbrief\Steckbrief-App-Production"
npx http-server
```

## Troubleshooting

### Logo wird nicht angezeigt
- Stelle sicher, dass die Ordnerstruktur erhalten bleibt:
  ```
  Steckbrief-App-Production/
  ├── index.html
  └── Rahmengebendes/Asgard-HO/Allgemeines/Fom Logo.jpg
  ```
- Der Pfad in index.html muss: `Rahmengebendes/Asgard-HO/Allgemeines/Fom Logo.jpg`

### Charts werden nicht angezeigt
- Überprüfe Internet-Verbindung (Chart.js wird von CDN geladen)
- Öffne Browser-Konsole (F12) und prüfe auf Fehler

### App lädt nicht
- Probiere einen anderen Browser
- Verwende einen lokalen Server statt Direktöffnung
- Überprüfe dass `index.html` 140KB+ groß ist

## Dateien von der ursprünglichen App

Diese Production-Version enthält NUR die notwendigen Dateien:

✅ **Dahinter**: 
- index.html (eigenständig, enthält alle Mock-Daten + CSS + JavaScript)
- Fom Logo.jpg

❌ **NICHT enthalten** (nicht nötig):
- *.py Skripte (für Datenanalyse/Entwicklung)
- PDF-Dateien (Quelldaten)
- Asgard-Datenbank-Verbindungen
- Entwicklungs-Tools

## Datenschutz & Sicherheit

Diese Version nutzt **Mock-Daten** (keine echten Personendaten):
- 🟢 Sicher zum Teilen und Demonstrieren
- 🟢 Keine Datenbankzugriffe erforderlich
- 🟢 DSGVO-konform (nur Demo-Daten)

## Nächste Schritte

1. **Starten**: Öffne `index.html` im Browser
2. **Testen**: Wechsle zwischen HSB und Studiengängen
3. **Filter**: Teste den neuen HSZ-Filter
4. **Chats**: Überprüfe ob alle Diagramme laden
5. **Daten**: Je nach Bedarf Mock-Daten anpassen

---

**Version**: 1.0.0  
**Datum**: 15. April 2026
