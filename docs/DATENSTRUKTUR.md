# DATENSTRUKTUR.md - Mock-Daten Referenz

## Überblick

Die App enthält integrierte Mock-Daten für 5 Hochschulbereiche mit 6 Studiengängen.

## Hochschulbereiche (HSB)

```json
{
  "id": "wm",
  "name": "Wirtschaft & Management",
  "farbe": "#00594D",
  "icon": "💼",
  "programmes": [...]
}
```

### HSB Liste
1. **WM** - Wirtschaft & Management
2. **IT** - Informatik & Digitalisierung  
3. **ING** - Ingenieurwesen
4. **WR** - Wirtschaftsrecht
5. **GUS** - Gesundheit & Soziales

## Studiengang-Struktur

```json
{
  "id": "WM_BA_BBA",
  "name": "Business Administration",
  "kurzname": "BBA",
  "abschluss": "Bachelor",
  "regelstudienzeit": 6,
  "creditpoints": 180,
  "hszensActive": ["München", "Hamburg", "Berlin", "Frankfurt", "Köln"],
  
  "rahmendaten": {
    "akkreditierung": "FIBAA",
    "akkreditierungsDatum": "November 2022",
    "imAngebotSeit": "2003",
    "ltg_studienfachgruppe": "Prof. Dr. Michael Schäfer",
    "zeitmodelle": ["Vollzeit", "Berufsbegleitend"],
    "ue": {
      "praxis": 2316,
      "virtuell": 870,
      "folgt": 160
    }
  },
  
  "entwicklungstrends": {
    "studierende_gesamt": 650,
    "studierende_delta": "+15 (+2,4%)",
    "studienbeginner": 185,
    "studienbeginner_fom_avg": 155,
    
    "zeitreihe_semester": ["2023", "2024", "2025", "2026"],
    "zeitreihe_ss": [746, 650, 575, 500],
    "zeitreihe_ws": [788, 712, 618, 530],
    "zeitreihe_fom_avg_ss": [732, 658, 592, 510],
    "zeitreihe_fom_avg_ws": [778, 695, 625, 545],
    
    "studienbeginner_zeitreihe_semester": ["2023", "2024", "2025", "2026"],
    "studienbeginner_zeitreihe_ss": [230, 185, 152, 135],
    "studienbeginner_zeitreihe_ws": [266, 229, 168, 145],
    "studienbeginner_zeitreihe_fom_avg_ss": [138, 130, 115, 105],
    "studienbeginner_zeitreihe_fom_avg_ws": [159, 140, 122, 115]
  },
  
  "anrechnungen": {
    "hochschulisch_pct": 42,
    "beruflich_pct": 38,
    "keine_pct": 20,
    "zeitreihe_semester": ["2022-WS", "2023-SS", "2023-WS", "2024-SS", "2024-WS", "2025-SS"],
    "hochschulisch_zeitreihe": [38, 39, 41, 42, 42, 42],
    "beruflich_zeitreihe": [42, 41, 39, 38, 38, 38],
    "keine_zeitreihe": [20, 20, 20, 20, 20, 20],
    "top_abschluesze": ["Betriebswirt", "Kaufmann", "Diplom", "Techniker", "Meister"]
  },
  
  "stammdaten": {
    "alter_avg": 28,
    "frauen_pct": 45,
    "maenner_pct": 55,
    "divers_pct": 0,
    "deutsche_pct": 92,
    "auslaender_pct": 8,
    "alter_distribution": [5, 15, 22, 25, 18, 10, 5]
  },
  
  "studienerfolg": {
    "abbrecherquote": 19.2,
    "abbrecherquote_fom_avg": 22.3,
    "absolventen_pct": 68,
    "absolventen_fom_avg": 62,
    "absolventen_pro_jahr": 156,
    "abbrecherquote_fachsemester": [12.5, 15.8, 18.2, 19.2, 18.8, 17.5, 15.2, 12.1],
    "abbrecherquote_fom_fachsemester": [18.2, 20.5, 22.3, 23.1, 22.8, 21.5, 19.2, 16.8]
  }
}
```

## Datenfelder Erklärung

### Rahmendaten
| Feld | Beschreibung |
|------|-------------|
| `akkreditierung` | Akkreditierungsagentur (z.B. FIBAA) |
| `akkreditierungsDatum` | Wann wurde akkreditiert |
| `imAngebotSeit` | Startjahr des Angebots |
| `ltg_studienfachgruppe` | Leiter der Studienfachgruppe |
| `zeitmodelle` | Angebotene Formate (Vollzeit, Berufsbegleitend) |
| `ue.praxis` | Unterrichtseinheiten in Präsenz |
| `ue.virtuell` | Online-Unterrichtseinheiten |
| `ue.folgt` | UE ohne Raumzuweisung |

### Entwicklungstrends
| Feld | Beschreibung |
|------|-------------|
| `zeitreihe_semester` | Array von Jahrzahlen (z.B. ["2023", "2024", "2025", "2026"]) |
| `zeitreihe_ss` | Sommersemester Studierendenzahlen |
| `zeitreihe_ws` | Wintersemester Studierendenzahlen |
| `zeitreihe_fom_avg_ss/ws` | FOM-Durchschnitt für Vergleich |

### Anrechnungen
| Feld | Beschreibung |
|------|-------------|
| `hochschulisch_pct` | % Anrechnung von universitärem Grad |
| `beruflich_pct` | % Anrechnung von Berufserfahrung |
| `keine_pct` | % ohne Anrechnung |
| `zeitreihe_semester` | Semester-Format: "YYYY-SS" oder "YYYY-WS" |
| `top_abschluesze` | Top 5 Abschlusstypen |

## Studiengänge nach HSB

### Wirtschaft & Management (wm)
- BBA - Business Administration (Bachelor)
- MBA - Master of Business Administration (Master)

### Informatik & Digitalisierung (it)
- BWI - Wirtschaftsinformatik (Bachelor)

### Ingenieurwesen (ing)
- BEI - Elektrotechnik (Bachelor)

### Wirtschaftsrecht (wr)
- BWR - Wirtschaftsrecht (Bachelor)

### Gesundheit & Soziales (gus)
- BS - Soziale Arbeit (Bachelor)

## Hochschulzentren pro Studiengang

| Studiengang | Aktive HSZ |
|------------|-----------|
| BBA | München, Hamburg, Berlin, Frankfurt, Köln |
| MBA | München, Hamburg, Berlin |
| BWI | Frankfurt, München, Hamburg |
| BWR | München, Berlin |
| BEI | München, Düsseldorf |
| BS | Berlin, Hamburg |

## Semester-Logik

### Aktuelles Semester automatisch erkannt
- **März - August** = Sommersemester (SS)
- **September - Februar** = Wintersemester (WS)

Beispiel: Der 15. April 2026 wird erkannt als **SS26** (aktuelles Semester)

### Datenreihen
- Alle `zeitreihe_semester` starten mit 2023 und enden mit 2026
- Daten sind in **aufsteigender** Reihenfolge (2023 = Index 0, 2026 = Index 3)
- In Tabellen werden sie **absteigend** angezeigt (2026 oben, 2023 unten)
- Aktuelles Semester wird mit grünem Hintergrund + ★ hervorgehoben

## Mock-Daten hier anpassen

Um die Mock-Daten zu ändern:

1. Öffne `index.html` mit einem Texteditor
2. Suche nach: `const mockData = {`
3. Ändere die Werte:
   ```javascript
   // Beispiel: Business Administration Sommersemester 2024 von 650 auf 700
   zeitreihe_ss: [746, 700, 575, 500],  // ← Hier: 650 → 700
   ```
4. Speichern und im Browser neu laden (F5)

## Performance-Hinweise

- Alle Daten sind im HTML eingebettet (keine externen API-Aufrufe)
- Mock-Daten: ~140KB Dateigröße
- Charts werden mit Chart.js von CDN geladen
- Für echte Datenbanken siehe: [Datenbank-Verbindung konfigurieren]

---

**Version**: 1.0.0  
**Datum**: 15. April 2026
