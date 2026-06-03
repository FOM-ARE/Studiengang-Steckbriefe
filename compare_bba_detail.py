"""Detailvergleich BBA: Excel (C_Studierendenzahlen) vs API (C_StudienEin_ausstieg)"""
import openpyxl
from collections import defaultdict

wb = openpyxl.load_workbook(r'D:\Users\anke.rebach\Documents\Studienabschluss.xlsx', data_only=True)
ws = wb.active

# Header-Index erstellen
headers = list(next(ws.iter_rows(min_row=1, max_row=1, values_only=True)))
print("Relevante Spalten:")
for i, h in enumerate(headers):
    if h in ('Produktkuerzel', 'Kohorte', 'Semester', 'Cluster_Statuskuerzel', 
             'Statuskuerzel', 'FachSem', 'Studienort', 'noch_eingeschrieben',
             'Regelstudienzeit', 'AnzahlVerlängerungsSem', 'Verlaengerungssem_Cluster'):
        print(f"  [{i}] {h}")

print()
print("=" * 80)
print("VERGLEICH: Excel vs API fuer BBA")
print("=" * 80)

# BBA filtern
bba_data = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[6] == 'BBA':
        bba_data.append(row)

print(f"\nExcel: {len(bba_data)} BBA-Datensaetze")
print()

# 1) Kohortenverteilung
kohorten = defaultdict(int)
for row in bba_data:
    kohorten[row[13]] += 1

print("--- Kohortenverteilung (Excel) ---")
for k in sorted(kohorten.keys()):
    print(f"  {k}: {kohorten[k]}")

# API Filter: Kohorte >= '2021-WS' (5 Jahre zurueck von 2026)
api_filter_kohorten = [k for k in sorted(kohorten.keys()) if k >= '2021-WS']
print(f"\nKohorten die der API-Filter (>= 2021-WS) erfasst: {api_filter_kohorten}")

# Nur BBA-Daten die dem API-Filter entsprechen
bba_api_filtered = [r for r in bba_data if r[13] >= '2021-WS']
print(f"BBA nach API-Kohortenfilter: {len(bba_api_filtered)} Datensaetze")
print()

# 2) Cluster-Verteilung MIT API-Filter
cluster_filtered = defaultdict(int)
for row in bba_api_filtered:
    cluster_filtered[row[27]] += 1

total_filtered = sum(cluster_filtered.values())
print("--- Cluster nach API-Kohortenfilter (Excel) ---")
for k, v in sorted(cluster_filtered.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v} ({v/total_filtered*100:.1f}%)")
print(f"  GESAMT: {total_filtered}")

print()
print("--- API-Ergebnis (aus C_StudienEin_ausstieg) ---")
print("  Abbrecher:              17.0%")
print("  Wechsler:               10.9%")
print("  aktiv (regulaer):       47.9%")
print("  aktiv (Verlaengerung):   9.0%")
print("  Absolventen:            15.3%")

print()
print("--- Vergleich: Excel (gefiltert) vs API ---")
# Mapping: Excel-Cluster -> API-Cluster
mapping = {
    'Abbrecher': 'Abbrecher',
    'Wechsler': 'Wechsler',
    'regulär eingeschrieben': 'aktiv (regulaer)',
    'eingeschrieben in der Verlängerung': 'aktiv (Verlaengerung)',
    'Absolventen': 'Absolventen'
}
api_pcts = {
    'Abbrecher': 17.0,
    'Wechsler': 10.9,
    'regulär eingeschrieben': 47.9,
    'eingeschrieben in der Verlängerung': 9.0,
    'Absolventen': 15.3
}

print(f"{'Kategorie':<40} {'Excel%':>8} {'API%':>8} {'Diff':>8}")
print("-" * 70)
for excel_cat, api_cat in mapping.items():
    excel_pct = cluster_filtered[excel_cat] / total_filtered * 100
    api_val = api_pcts[excel_cat]
    diff = excel_pct - api_val
    print(f"  {excel_cat:<38} {excel_pct:>7.1f}% {api_val:>7.1f}% {diff:>+7.1f}%")

print()
print()
# 3) HSZ Ausschluss pruefen
print("--- Hochschulzentren in Excel (BBA) ---")
hsz_counts = defaultdict(int)
for row in bba_api_filtered:
    hsz_counts[row[11]] += 1  # Studienort/Kuerzel

excluded_hsz = ['Bangalore', 'Pune', 'Ahmedabad', 'Sofia', 'Venlo', 'Luxemburg']
excluded_short = {'BAN': 'Bangalore', 'PUN': 'Pune', 'AHM': 'Ahmedabad', 'SOF': 'Sofia', 'VEN': 'Venlo', 'LUX': 'Luxemburg'}
print("  Potentiell API-excluded HSZ:")
for code in sorted(hsz_counts.keys()):
    # Check if it's an excluded one
    for ex in excluded_hsz:
        if ex.lower() in str(code).lower() or code in excluded_short:
            print(f"    {code}: {hsz_counts[code]} Datensaetze (EXCLUDED in API)")
            break

# 4) Semester-Filter
print()
print("--- Semester-Filter ---")
semester_counts = defaultdict(int)
for row in bba_api_filtered:
    semester_counts[row[12]] += 1
print(f"  Semester in Excel: {dict(semester_counts)}")
print()
print("  API-Query hat KEINEN Semester-Filter (nur Kohorte >= 5J zurueck)")
print("  Excel zeigt nur aktuelle Snapshot-Daten (Semester = 2026-SS)")

print()
print()
print("=== ZUSAMMENFASSUNG DER UNTERSCHIEDE ===")
print()
print("1. DATENQUELLE:")
print("   Excel:  Basiert auf C_Studierendenzahlen (Snapshot aktuelle Semester)")
print("   API:    Basiert auf C_StudienEin_ausstieg (Ein-/Ausstiegshistorie)")
print()
print("2. KOHORTENFILTER:")
print(f"   Excel:  Alle Kohorten vorhanden ({min(kohorten.keys())} bis {max(kohorten.keys())})")
print(f"   API:    Nur Kohorten >= 2021-WS (letzte 5 Jahre)")
print()
print("3. HSZ-AUSSCHLUSS:")
print("   Excel:  Keine HSZ ausgeschlossen")
print("   API:    Bangalore, Pune, Ahmedabad, Sofia, Venlo, Luxemburg EXCLUDED")
print()
print("4. GUELTIGKEITSFILTER:")
print("   Excel:  Kein Filter auf 'Gueltige_Codierung'")
print("   API:    Nur Gueltige_Codierung = 1")
print()
print("5. CLUSTER-NAMEN:")
print("   Excel:  'regulaer eingeschrieben', 'Absolventen'")
print("   API:    'Eingeschrieben' (mit RSZ 0/1), 'Absolvent'")
