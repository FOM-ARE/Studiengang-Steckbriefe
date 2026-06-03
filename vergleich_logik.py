"""Vergleich der Klassifikationslogik: CSV/Excel vs API"""
import csv
from collections import defaultdict

# CSV lesen (die 543 ungültigen Einträge)
with open(r'D:\Users\anke.rebach\Documents\BBA_Ungueltige_Codierung_543.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f, delimiter=';')
    rows = list(reader)

print("=" * 80)
print("ANALYSE: Klassifikationslogik in den Daten")
print("=" * 80)

# 1) Wieviele LehrgangsIDs haben mehrere Einträge?
lehrgang_map = defaultdict(list)
for r in rows:
    lehrgang_map[r['LehrgangsID']].append(r)

single = sum(1 for v in lehrgang_map.values() if len(v) == 1)
multi = sum(1 for v in lehrgang_map.values() if len(v) > 1)
print(f"\n1) STRUKTUR DER 543 UNGÜLTIGEN EINTRÄGE:")
print(f"   Distinct LehrgangsIDs: {len(lehrgang_map)}")
print(f"   Davon mit 1 Eintrag:   {single}")
print(f"   Davon mit >1 Einträge: {multi}")

# Beispiel: LehrgangsID mit vielen Einträgen
if multi > 0:
    example_lg = max(lehrgang_map.items(), key=lambda x: len(x[1]))
    print(f"\n   Beispiel LehrgangsID {example_lg[0]} ({len(example_lg[1])} Einträge):")
    for r in example_lg[1][:5]:
        print(f"     StudienEintragID={r['StudienEintragID']}, Cluster={r['AusstiegsCluster']}, "
              f"Status={r['Ausstiegsstatus']}, RSZ={r['RegelstudienzeitAbgeschlossen']}, FS={r['AktuellesFachsemester']}")

# 2) AusstiegsCluster-Werte in der CSV
print(f"\n2) AUSSTIEGSCLUSTER-WERTE (C_StudienEin_ausstieg):")
cluster_vals = defaultdict(int)
for r in rows:
    key = f"{r['AusstiegsCluster']}|Status={r['Ausstiegsstatus']}|RSZ={r['RegelstudienzeitAbgeschlossen']}"
    cluster_vals[key] += 1
for k, v in sorted(cluster_vals.items(), key=lambda x: -x[1]):
    print(f"   {k}: {v}")

# 3) Vergleich der Logik
print(f"\n\n{'=' * 80}")
print("VERGLEICH: Excel-Logik vs API-Logik")
print("=" * 80)

print("""
┌─────────────────────────────────────────────────────────────────────────┐
│ EXCEL (Studienabschluss.xlsx) - Spalte "Cluster_Statuskuerzel"          │
├─────────────────────────────────────────────────────────────────────────┤
│ Quelle: C_Studierendenzahlen (Snapshot-Tabelle)                         │
│ Zähleinheit: studiengang_tn_ID (1 pro Studiengang-Teilnahme)            │
│                                                                         │
│ Kategorien:                                                             │
│   • "regulär eingeschrieben"              = noch_eingeschrieben=Y       │
│                                             UND Regelstudienzeit='laufend'│
│   • "eingeschrieben in der Verlängerung"  = noch_eingeschrieben=Y       │
│                                             UND AnzahlVerlängerungsSem>0│
│   • "Absolventen"                         = Statuskuerzel enthält 'A'   │
│   • "Abbrecher"                           = Statuskuerzel = 'K'         │
│   • "Wechsler"                            = Statuskuerzel enthält 'W'   │
│                                                                         │
│ Besonderheit: 1 Zeile pro Student pro SG (aktueller Snapshot)           │
│ Kein Feld "Gueltige_Codierung" → alle Einträge werden gezählt           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│ API (app.py) - Feld "AusstiegsCluster"                                  │
├─────────────────────────────────────────────────────────────────────────┤
│ Quelle: C_StudienEin_ausstieg (Verlaufs-/Historiendaten)                │
│ Zähleinheit: StudienEintragID (1 pro Einschreibungssegment)             │
│                                                                         │
│ Kategorien (in calc_fachsem_pct):                                       │
│   • "aktiv (regulär)"      = AusstiegsCluster='Eingeschrieben'          │
│                               UND RegelstudienzeitAbgeschlossen=0       │
│   • "aktiv (Verlängerung)" = AusstiegsCluster='Eingeschrieben'          │
│                               UND RegelstudienzeitAbgeschlossen=1       │
│   • "Absolventen"          = AusstiegsCluster='Absolvent'               │
│   • "Abbrecher"            = AusstiegsCluster='Abbrecher'               │
│   • "Wechsler"             = AusstiegsCluster='Wechsler'                │
│                                                                         │
│ Besonderheit: 1 Zeile pro StudienEintrag (kann mehrere pro Lehrgang geben)│
│ Filter: Gueltige_Codierung=1 → nur eindeutige Einträge                 │
│ Filter: Kohorte >= 5 Jahre zurück UND <= aktuelles Semester             │
│ Filter: Auslands-HSZ excluded                                           │
└─────────────────────────────────────────────────────────────────────────┘
""")

print("UNTERSCHIEDE IN DER LOGIK:")
print("-" * 80)
print("""
1. QUELLE/TABELLE:
   Excel: C_Studierendenzahlen (Snapshot - "wer ist JETZT eingeschrieben/was?")
   API:   C_StudienEin_ausstieg (Verlauf - "wann ein-/ausgestiegen?")

2. ZÄHLEINHEIT:
   Excel: 1 Zeile pro studiengang_tn_ID = 1 pro Studiengang-Teilnahme (FINAL-Status)
   API:   1 Zeile pro StudienEintragID = 1 pro Einschreibungssegment
          → Ein Lehrgang kann MEHRERE StudienEinträge haben (z.B. Verlängerungen)
          → ABER: mit Gueltige_Codierung=1 wird nur der gültige Eintrag gezählt

3. VERLÄNGERUNG ERKENNUNG:
   Excel: AnzahlVerlängerungsSem > 0 (explizites Feld)
   API:   RegelstudienzeitAbgeschlossen = 1 (RSZ überschritten)
   → POTENTIELLE DIFFERENZ: Ein Student könnte RSZ=1 haben aber
     AnzahlVerlängerungsSem=0 oder umgekehrt

4. ABSOLVENTEN-ERKENNUNG:
   Excel: Statuskuerzel enthält Abschluss-Kennung
   API:   AusstiegsCluster = 'Absolvent'
   → Sollte identisch sein (beide von DWH klassifiziert)

5. FILTER:
   Excel: Kein Kohortenfilter, kein HSZ-Ausschluss, keine Gueltige_Codierung
   API:   Kohorte 5J zurück bis aktuelles Semester, Auslands-HSZ excluded,
          nur Gueltige_Codierung=1
""")

print("\nFAZIT:")
print("=" * 80)
print("""
Die GRÖSSTE logische Differenz ist Punkt 3: "Verlängerung-Erkennung"
- Excel prüft: Hat der Student explizit Verlängerungssemester gebucht?
- API prüft:   Ist die Regelstudienzeit überschritten (RSZ=1)?

Das kann zu unterschiedlichen Zuordnungen führen wenn:
- Jemand noch in der RSZ ist aber schon ein Verlängerungssem gebucht hat (Excel: Verlängerung, API: regulär)
- Jemand die RSZ überschritten hat aber kein offizielles Verlängerungssem hat (Excel: regulär, API: Verlängerung)

Die Quoten-Differenzen (Absolventen -53, Verlängerung +29, etc.) passen zu diesem Muster.
""")
