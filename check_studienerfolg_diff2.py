"""Compare C_StudienEin_ausstieg vs App SJS-based calculation."""
import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
c = conn.cursor()

# 1) C_StudienEin_ausstieg mit Gueltige_Codierung=1
c.execute("""
SELECT
    c.AusstiegsCluster,
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
  AND c.Gueltige_Codierung = 1
GROUP BY c.AusstiegsCluster
ORDER BY Anzahl DESC
""")
rows = c.fetchall()
total = sum(r[1] for r in rows)
print(f"=== C_StudienEin_ausstieg (Gueltige_Codierung=1) ===")
print(f"Total: {total}")
for r in rows:
    print(f"  {str(r[0] or 'NULL'):20s}: {r[1]:5d} ({round(r[1]/total*100,1)}%)")

# 2) C_StudienEin_ausstieg OHNE Gueltige_Codierung Filter
c.execute("""
SELECT
    c.AusstiegsCluster,
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
GROUP BY c.AusstiegsCluster
ORDER BY Anzahl DESC
""")
rows2 = c.fetchall()
total2 = sum(r[1] for r in rows2)
print(f"\n=== C_StudienEin_ausstieg (ALLE, ohne Gueltige_Codierung) ===")
print(f"Total: {total2}")
for r in rows2:
    print(f"  {str(r[0] or 'NULL'):20s}: {r[1]:5d} ({round(r[1]/total2*100,1)}%)")

# 3) App-Ergebnis zum Vergleich
print(f"\n=== App (SJS-basiert) ===")
print(f"Total: 12518")
print(f"  Eingeschrieben_R:  5995 (47.9%)")
print(f"  Eingeschrieben_V:  1120 (8.9%)")
print(f"  Abbrecher:         2127 (17.0%)")
print(f"  Absolvent:         1925 (15.4%)")
print(f"  Wechsler:          1351 (10.8%)")

conn.close()
