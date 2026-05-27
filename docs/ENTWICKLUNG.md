# ENTWICKLUNG.md - Anleitung zur Weiterentwicklung

## Projektstruktur verstehen

### Dateiaufbau

Die `index.html` ist vollständig eigenständig und enthält:

```html
<!DOCTYPE html>
<html>
<head>
    <!-- Meta & Title -->
    <meta charset="UTF-8">
    <title>FOM - Studiengang-Steckbriefe</title>
    
    <!-- Chart.js von CDN -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    
    <!-- CSS (intern) -->
    <style>/* ~500 Zeilen CSS */</style>
</head>
<body>
    <!-- HTML Struktur -->
    <header>...</header>
    <div class="container">...</div>
    
    <!-- JavaScript (intern) ~1300 Zeilen -->
    <script>
        const mockData = { ... }
        function getCurrentSemester() { ... }
        function renderHSBGrid() { ... }
        // ... viele weitere Funktionen
    </script>
</body>
</html>
```

## Wichtigste Funktionen

### 1. getCurrentSemester()
Bestimmt automatisch das aktuelle Semester:
```javascript
function getCurrentSemester() {
    const now = new Date();
    const month = now.getMonth() + 1;
    if (month >= 3 && month <= 8) {
        return { type: 'SS', year: now.getFullYear(), label: year + ' SS' };
    } else {
        return { type: 'WS', year: now.getFullYear(), label: year + ' WS' };
    }
}
```

### 2. renderHSBGrid()
Zeigt Hochschulbereich-Karten auf der Startseite

### 3. showDetail(hsbId)
Wechselt zur Detailansicht des gewählten HSB

### 4. renderFilterSection(hsb)
Rendert die Selects für:
- Studiengang-Auswahl
- HSZ-Filter (nur aktive für den Studiengang)

### 5. renderTabs() & renderRahmendaten/Trends/etc.
Rendert die verschiedenen Content-Tabs

### 6. buildTrendsTable(p) & buildStudienanfaengerTable(p)
Erstellt die Tabellen mit intelligenter Semester-Sortierung

### 7. initChartsForTrends/Studienbeginner/etc.
Initialisiert Chart.js Diagramme

## Häufige Anpassungen

### 1. Mock-Daten ändern

**Ort**: Im `<script>` Tag, `const mockData = {`

**Beispiel: Neue HSZ für einen Studiengang hinzufügen**
```javascript
{
    id: 'WM_BA_BBA',
    name: 'Business Administration',
    hszensActive: ['München', 'Hamburg', 'Berlin', 'Frankfurt', 'Köln', 'Köln'], // ← Neu hinzugefügt
    // ...
}
```

**Beispiel: Studiendenzahl aktualisieren**
```javascript
entwicklungstrends: {
    vollständig: 650,    // ← Ändern auf z.B. 700
    entwicklungstrends_delta: '+15 (+2,4%)',
    zeitreihe_ss: [746, 650, 575, 500],  // ← Oder hier die Werte anpassen
    // ...
}
```

### 2. Neuen Studiengang hinzufügen

1. Finde das HSB-Array (z.B. `wm`, `it`):
```javascript
hsbs: [
    {
        id: 'wm',
        name: 'Wirtschaft & Management',
        programmes: [
            // Existierende Programme...
            // Neues hinzufügen ↓
            {
                id: 'WM_BA_NEUES',
                name: 'Neuer Studiengang',
                abschluss: 'Bachelor',
                // ... alle anderen Felder kopieren von existierendem Studiengang
            }
        ]
    }
]
```

2. Alle erforderlichen Felder kopieren von einem bestehenden Studiengang
3. Die `id` muss einzigartig sein
4. HTML neu laden

### 3. CSS anpassen

**Ort**: Im `<style>` Tag

**Beispiel: Header-Farbe ändern**
```css
:root {
    --fom-primary: #00998a;  /* ← Hier ändern */
    --fom-primary-dark: #007a6e;
    /* ... */
}
```

**Beispiel: Tabellen-Stil ändern**
```css
.trends-table tbody tr:hover {
    background: var(--fom-primary-pale) !important;
}
```

### 4. HTML-Struktur ändern

Die Struktur ist relativ fix, aber HTML-Teile können in den `render*`-Funktionen angepasst werden.

**Beispiel: Neue Badge in HSZ-Anzeige**
```javascript
function renderRahmendaten(p) {
    return `<div style="...">
        <h3>Aktive Hochschulzentren (${p.hszensActive.length})</h3>
        <div style="display: flex; flex-wrap: wrap; gap: 8px;">
            ${p.hszensActive.map(h => `
                <span style="...">
                    ${h} 🏫  <!-- ← Emoji hinzugefügt -->
                </span>
            `).join('')}
        </div>
    </div>`;
}
```

## Debugging

### Browser-Konsole öffnen
- Drücke **F12** oder **Ctrl+Shift+I**
- Gehe zu **Console** Tab

### Häufige Fehler

**"Cannot read property 'hszensActive' of undefined"**
- Bedeutet: Studiengang/Program ist nicht geladen
- Überprüfe die Bedingung: `if (currentProgramme)`

**"Chart is not defined"**
- Chart.js hatte Probleme zu laden von CDN
- Überprüfe Internet-Verbindung
- Oder lade Chart.js lokal

**Emoji werden als "?" angezeigt**
- Datei-Encoding muss UTF-8 sein
- Überprüfe HTML5 Meta-Tag: `<meta charset="UTF-8">`

## Performance-Tipps

### Aktuelle Optimierungen
- ✅ Alle Daten sind inline (keine API-Aufrufe)
- ✅ CSS ist inline (keine separaten Stylesheet-Aufrufe)
- ✅ JavaScript ist inline (keine separaten Dateien)

### Bei echten Daten
- Erwäge Daten-Caching
- Lade Charts lazy (nur wenn Tab aktiv)
- Komprimiere die HTML-Datei mit `gzip`

## Semester-System verstehen

Das System erkennt automatisch das aktuelle Semester:
```javascript
const current = getCurrentSemester();
// Beispiel April 2026: { type: 'SS', year: 2026, label: '2026 SS' }

// In Tabellen wird dann die Zeile hervorgehoben:
const isCurrentSS = semesters[i] == current.year && current.type === 'SS';
if (isCurrentSS) {
    // Grüner Hintergrund + Stern ★
}
```

**wichtig**: Die `zeitreihe_semester` darf NUR Jahrzahlen enthalten:
```javascript
zeitreihe_semester: ['2023', '2024', '2025', '2026']  // ✅ RICHTIG
// NICHT:
zeitreihe_semester: ['2023-SS', '2023-WS', '2024-SS', ...] // ❌ FALSCH
```

## Nächste Schritte für Production

### Datenquellen integrieren
```javascript
// Statt Mock-Daten:
const fetchData = async () => {
    const response = await fetch('/api/studiengaenge');
    const mockData = await response.json();
    renderHSBGrid();
}
```

### Datenbank-Verbindung
Siehe `.env` und `asgard_import/` für:
- MariaDB (Staging)
- SQL Server (DWH)

### Deployment
- Kopiere den ganzen `Steckbrief-App-Production/` Ordner auf den Server
- Serviere mit beliebigem Web-Server
- Keine Installation/Dependencies nötig

## Code-Konventionen

- **Funktionsnamen**: `camelCase` (z.B. `renderHSBGrid`)
- **Variables`: `camelCase` (z.B. `currentProgramme`)
- **CSS-Klassen**: `kebab-case` (z.B. `trends-table`)
- **HTML-IDs**: `kebab-case` (z.B. `filterSection`)
- **Konstanten**: `UPPER_CASE` (z.B. `PRODUCTION_MODE`)

## Hilfsynotizen

### Alle Higschulbereiche
```javascript
const hsbIds = ['wm', 'it', 'ing', 'wr', 'gus'];
const hsbNames = {
    'wm': 'Wirtschaft & Management',
    'it': 'Informatik & Digitalisierung',
    'ing': 'Ingenieurwesen',
    'wr': 'Wirtschaftsrecht',
    'gus': 'Gesundheit & Soziales'
};
```

### Chart-Farben
```javascript
const chartColors = {
    'wm': 'rgba(0, 153, 138, 0.8)',    // Teal
    'it': 'rgba(5, 115, 193, 0.8)',    // Blue
    'ing': 'rgba(143, 182, 62, 0.8)',  // Green
    'wr': 'rgba(208, 153, 16, 0.8)',   // Orange
    'gus': 'rgba(0, 176, 80, 0.8)'     // Light Green
};
```

---

**Version**: 1.0.0  
**Datum**: 15. April 2026  
**Fragen?** Siehe README.md
