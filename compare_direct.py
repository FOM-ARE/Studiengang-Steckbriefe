import openpyxl
from collections import defaultdict

wb = openpyxl.load_workbook(r'D:\Users\anke.rebach\Documents\Studienabschluss.xlsx', data_only=True)
ws = wb.active

# BBA mit Kohorte >= 2021-WS, <= 2026-SS (gleicher Filter wie neue API)
eingeschrieben_reg = 0
eingeschrieben_verl = 0
abbrecher = 0
absolventen = 0
wechsler = 0

for row in ws.iter_rows(min_row=2, values_only=True):
    if row[6] == 'BBA' and row[13] >= '2021-WS' and row[13] <= '2026-SS':
        cluster = row[27]  # Cluster_Statuskuerzel
        if not cluster:
            continue
        if 'eingeschrieben' in cluster.lower() and 'verl' in cluster.lower():
            eingeschrieben_verl += 1
        elif 'eingeschrieben' in cluster.lower():
            eingeschrieben_reg += 1
        elif 'Abbrecher' in cluster:
            abbrecher += 1
        elif 'Absolventen' in cluster:
            absolventen += 1
        elif 'Wechsler' in cluster:
            wechsler += 1

excel_total = eingeschrieben_reg + eingeschrieben_verl + abbrecher + absolventen + wechsler

print("DIREKTER VERGLEICH: Excel vs API (BBA, Kohorte 2021-WS bis 2026-SS)")
print("=" * 70)
print()
print(f"{'Kategorie':<35} {'Excel':>8} {'API':>8} {'Diff':>8}")
print("-" * 70)
print(f"{'regulaer eingeschrieben':<35} {eingeschrieben_reg:>8} {'5629':>8} {eingeschrieben_reg - 5629:>+8}")
print(f"{'eingeschrieben in Verlaengerung':<35} {eingeschrieben_verl:>8} {'1098':>8} {eingeschrieben_verl - 1098:>+8}")
print(f"{'Abbrecher':<35} {abbrecher:>8} {'2038':>8} {abbrecher - 2038:>+8}")
print(f"{'Absolventen':<35} {absolventen:>8} {'1759':>8} {absolventen - 1759:>+8}")
print(f"{'Wechsler':<35} {wechsler:>8} {'1340':>8} {wechsler - 1340:>+8}")
print("-" * 70)
print(f"{'GESAMT':<35} {excel_total:>8} {'11864':>8} {excel_total - 11864:>+8}")
print()
print("API-Werte stammen aus C_StudienEin_ausstieg mit:")
print("  Gueltige_Codierung=1, Kohorte >= 2021-WS AND <= 2026-SS")
print("  Hochschulzentrum NOT IN (Bangalore,Pune,Ahmedabad,Sofia,Venlo,Luxemburg)")
