"""Vergleich BBA Studienerfolg: Excel vs API"""
import openpyxl
import json
import urllib.request
from collections import defaultdict

# 1) Excel lesen
wb = openpyxl.load_workbook(r'D:\Users\anke.rebach\Documents\Studienabschluss.xlsx', data_only=True)
ws = wb.active

# Header lesen
headers = [cell for cell in next(ws.iter_rows(min_row=1, max_row=1, values_only=True))]
print("=== EXCEL: BBA Studienerfolg-Daten ===")
print(f"Spalten: {len(headers)}")
print()

# BBA filtern und aggregieren
bba_data = []
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[6] == 'BBA':  # Produktkuerzel
        bba_data.append(row)

print(f"BBA Zeilen gesamt: {len(bba_data)}")
print()

# Cluster_Statuskuerzel (Spalte 27)
cluster_counts = defaultdict(int)
for row in bba_data:
    cluster = row[27]
    cluster_counts[cluster] += 1

print("--- Cluster_Statuskuerzel ---")
total = sum(cluster_counts.values())
for k, v in sorted(cluster_counts.items(), key=lambda x: -x[1]):
    pct = v / total * 100
    print(f"  {k}: {v} ({pct:.1f}%)")
print(f"  GESAMT: {total}")
print()

# Abschlussquote berechnen (nur abgeschlossene Kohorten)
# Kohorten die mindestens Regelstudienzeit + 2 Semester alt sind
kohorten = defaultdict(lambda: defaultdict(int))
for row in bba_data:
    kohorte = row[13]  # Kohorte
    cluster = row[27]  # Cluster_Statuskuerzel
    kohorten[kohorte][cluster] += 1

# Nur Kohorten die "fertig" sind (keine regulär eingeschriebenen mehr)
print("--- Abschlussquoten nach Kohorte (nur abgeschlossene Kohorten) ---")
print(f"{'Kohorte':<12} {'Absolv.':>8} {'Abbrech.':>8} {'Wechsler':>8} {'Gesamt':>8} {'Absolv%':>8} {'Abbruch%':>8} {'Schwund%':>8}")
print("-" * 85)

fertige_kohorten = []
for k in sorted(kohorten.keys()):
    s = kohorten[k]
    reg = s.get('regulär eingeschrieben', 0)
    verl = s.get('eingeschrieben in der Verlängerung', 0)
    # Nur Kohorten wo niemand mehr eingeschrieben ist
    if reg == 0 and verl == 0:
        fertige_kohorten.append(k)
        absolventen = s.get('Absolventen', 0)
        abbrecher = s.get('Abbrecher', 0)
        wechsler = s.get('Wechsler', 0)
        gesamt = absolventen + abbrecher + wechsler
        if gesamt > 0:
            absolv_pct = absolventen / gesamt * 100
            abbruch_pct = abbrecher / gesamt * 100
            schwund_pct = (abbrecher + wechsler) / gesamt * 100
            print(f"{k:<12} {absolventen:>8} {abbrecher:>8} {wechsler:>8} {gesamt:>8} {absolv_pct:>7.1f}% {abbruch_pct:>7.1f}% {schwund_pct:>7.1f}%")

print()
# Gesamtsumme über fertige Kohorten
total_abs = sum(kohorten[k].get('Absolventen', 0) for k in fertige_kohorten)
total_abb = sum(kohorten[k].get('Abbrecher', 0) for k in fertige_kohorten)
total_wec = sum(kohorten[k].get('Wechsler', 0) for k in fertige_kohorten)
total_all = total_abs + total_abb + total_wec
if total_all > 0:
    print(f"GESAMT (fertige Kohorten): Absolv={total_abs} ({total_abs/total_all*100:.1f}%), Abbruch={total_abb} ({total_abb/total_all*100:.1f}%), Wechsler={total_wec} ({total_wec/total_all*100:.1f}%)")

print()
print()

# 2) API Daten holen
print("=== API: BBA Studienerfolg-Daten ===")
try:
    req = urllib.request.Request('http://localhost:5000/api/steckbrief/BBA/studienerfolg')
    with urllib.request.urlopen(req, timeout=30) as resp:
        api_data = json.loads(resp.read().decode())
    
    if api_data.get('success'):
        data = api_data['data']
        print(json.dumps(data, indent=2, ensure_ascii=False)[:3000])
    else:
        print(f"API Fehler: {api_data}")
except Exception as e:
    print(f"API Fehler: {e}")
