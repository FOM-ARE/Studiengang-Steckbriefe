import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
cur = conn.cursor()

# Kohorte-Verteilung BBA mit aktuellem Filter
sql = """
SELECT Kohorte, AusstiegsCluster, RegelstudienzeitAbgeschlossen AS RSZ, COUNT(*) AS Anzahl
FROM BCW_DWH.dwh.C_StudienEin_ausstieg
WHERE Institut = 'FOM' AND Gueltige_Codierung = 1
  AND Produktkuerzel = 'BBA'
  AND Kohorte >= '2021-WS'
  AND Kohorte <= '2026-SS'
  AND Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
GROUP BY Kohorte, AusstiegsCluster, RegelstudienzeitAbgeschlossen
ORDER BY Kohorte, AusstiegsCluster
"""

cur.execute(sql)
rows = cur.fetchall()

# Pivot
from collections import defaultdict

kohorten = defaultdict(lambda: defaultdict(int))
for r in rows:
    kohorte, cluster, rsz, anzahl = r
    key = cluster if cluster != "Eingeschrieben" else f"Eingeschr_RSZ{rsz}"
    kohorten[kohorte][key] += anzahl
    kohorten[kohorte]["total"] += anzahl

print(
    f"{'Kohorte':<10} {'Total':>6} {'Eingeschr_R':>12} {'Eingeschr_V':>12} {'Abbrecher':>10} {'Absolvent':>10} {'Wechsler':>9} {'%aktiv':>7}"
)
print("-" * 80)
gesamt_total = 0
gesamt_reg = 0
gesamt_verl = 0
for k in sorted(kohorten.keys()):
    d = kohorten[k]
    total = d["total"]
    reg = d.get("Eingeschr_RSZ0", 0)
    verl = d.get("Eingeschr_RSZ1", 0)
    abb = d.get("Abbrecher", 0)
    abv = d.get("Absolvent", 0)
    wech = d.get("Wechsler", 0)
    pct_aktiv = (reg + verl) / total * 100
    print(
        f"{k:<10} {total:>6} {reg:>12} {verl:>12} {abb:>10} {abv:>10} {wech:>9} {pct_aktiv:>6.1f}%"
    )
    gesamt_total += total
    gesamt_reg += reg
    gesamt_verl += verl

print("-" * 80)
print(
    f"{'GESAMT':<10} {gesamt_total:>6} {gesamt_reg:>12} {gesamt_verl:>12} {'':>10} {'':>10} {'':>9} {(gesamt_reg + gesamt_verl) / gesamt_total * 100:>6.1f}%"
)
print()
print("Ohne 2025-WS und 2026-SS:")
total_alt = 0
reg_alt = 0
verl_alt = 0
for k in sorted(kohorten.keys()):
    if k >= "2025-WS":
        continue
    d = kohorten[k]
    total_alt += d["total"]
    reg_alt += d.get("Eingeschr_RSZ0", 0)
    verl_alt += d.get("Eingeschr_RSZ1", 0)
print(
    f"  Total: {total_alt}, Regulaer: {reg_alt} ({reg_alt / total_alt * 100:.1f}%), Verlaengerung: {verl_alt} ({verl_alt / total_alt * 100:.1f}%)"
)
print(f"  Aktiv gesamt: {reg_alt + verl_alt} ({(reg_alt + verl_alt) / total_alt * 100:.1f}%)")

conn.close()
