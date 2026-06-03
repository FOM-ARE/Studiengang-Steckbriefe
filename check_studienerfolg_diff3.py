"""Check C_StudienEin_ausstieg split by Ausstiegsstatus for Eingeschrieben."""
import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
c = conn.cursor()

# Eingeschrieben aufgeschlüsselt nach Ausstiegsstatus
c.execute("""
SELECT
    c.Ausstiegsstatus,
    c.Ausstiegsstatus_lang,
    COUNT(*) AS Anzahl
FROM BCW_DWH.dwh.C_StudienEin_ausstieg c
INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = c.StudienEintragID
INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
WHERE l.Institut = 'FOM'
  AND p.Testperson = 0
  AND l.Produktkuerzel IN ('BBA','BBAb','BBAd','BBAn')
  AND l.Kohorte >= '2021-WS'
  AND l.Kohorte <= '2026-SS'
  AND l.Hochschulzentrum NOT IN ('Venlo','Sofia','Bangalore','Pune','Ahmedabad','Luxemburg')
  AND c.AusstiegsCluster = 'Eingeschrieben'
GROUP BY c.Ausstiegsstatus, c.Ausstiegsstatus_lang
ORDER BY Anzahl DESC
""")
rows = c.fetchall()
total_eingeschr = sum(r[2] for r in rows)

# Total (alle Cluster, ohne NULL)
c.execute("""
SELECT COUNT(*) FROM BCW_DWH.dwh.C_StudienEin_ausstieg c
INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = c.StudienEintragID
INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
WHERE l.Institut = 'FOM' AND p.Testperson = 0
  AND l.Produktkuerzel IN ('BBA','BBAb','BBAd','BBAn')
  AND l.Kohorte >= '2021-WS' AND l.Kohorte <= '2026-SS'
  AND l.Hochschulzentrum NOT IN ('Venlo','Sofia','Bangalore','Pune','Ahmedabad','Luxemburg')
  AND c.AusstiegsCluster IS NOT NULL
""")
total_all = c.fetchone()[0]

print(f"Gesamt (ohne NULL): {total_all}")
print(f"Eingeschrieben gesamt: {total_eingeschr} ({round(total_eingeschr/total_all*100,1)}%)")
print()
print(f"{'Status':<6} {'Status_lang':<40} {'Anzahl':>6} {'% Gesamt':>10} {'% Eingeschr':>12}")
print("-" * 80)

verl = 0
reg = 0
for r in rows:
    status = r[0] or ''
    status_lang = r[1] or ''
    cnt = r[2]
    pct_all = round(cnt / total_all * 100, 1)
    pct_ein = round(cnt / total_eingeschr * 100, 1)
    print(f"{status:<6} {status_lang:<40} {cnt:>6} {pct_all:>9.1f}% {pct_ein:>11.1f}%")
    if 'V' in status and status != 'WSGO':
        verl += cnt
    else:
        reg += cnt

print()
print(f"Regulaer (nicht V): {reg} ({round(reg/total_all*100,1)}%)")
print(f"Verlaengerer (V):   {verl} ({round(verl/total_all*100,1)}%)")
print()
print(f"=== Vergleich ===")
print(f"C_StudienEin_ausstieg aktiv regulaer: {reg}/{total_all} = {round(reg/total_all*100,1)}%")
print(f"App (SJS-basiert) aktiv regulaer:     5995/12518 = 47.9%")

conn.close()
