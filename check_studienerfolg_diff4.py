"""Check with RegelstudienzeitAbgeschlossen=1."""
import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
c = conn.cursor()
c.execute("""
SELECT
    c.AusstiegsCluster,
    c.Ausstiegsstatus,
    COUNT(*) AS Anzahl
FROM BCW_DWH.dwh.C_StudienEin_ausstieg c
INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = c.StudienEintragID
INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
WHERE l.Institut = 'FOM' AND p.Testperson = 0
  AND l.Produktkuerzel IN ('BBA','BBAb','BBAd','BBAn')
  AND l.Kohorte >= '2021-WS' AND l.Kohorte <= '2026-SS'
  AND l.Hochschulzentrum NOT IN ('Venlo','Sofia','Bangalore','Pune','Ahmedabad','Luxemburg')
  AND c.RegelstudienzeitAbgeschlossen = 1
GROUP BY c.AusstiegsCluster, c.Ausstiegsstatus
ORDER BY c.AusstiegsCluster, Anzahl DESC
""")
rows = c.fetchall()
total = sum(r[2] for r in rows if r[0] is not None)
aktiv_reg = sum(r[2] for r in rows if r[0] == 'Eingeschrieben' and r[1] != 'V')
aktiv_v = sum(r[2] for r in rows if r[0] == 'Eingeschrieben' and r[1] == 'V')
print(f"Mit RegelstudienzeitAbgeschlossen=1:")
print(f"  Total (ohne NULL): {total}")
print(f"  Aktiv regulaer: {aktiv_reg} ({round(aktiv_reg/total*100,1)}%)")
print(f"  Aktiv Verlaengerung: {aktiv_v} ({round(aktiv_v/total*100,1)}%)")
for cluster in ['Abbrecher', 'Absolvent', 'Wechsler']:
    cnt = sum(r[2] for r in rows if r[0] == cluster)
    print(f"  {cluster}: {cnt} ({round(cnt/total*100,1)}%)")

# Auch ohne RSZ-Filter: mit Gueltige_Codierung=1
c.execute("""
SELECT
    c.AusstiegsCluster,
    c.Ausstiegsstatus,
    COUNT(*) AS Anzahl
FROM BCW_DWH.dwh.C_StudienEin_ausstieg c
INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = c.StudienEintragID
INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
WHERE l.Institut = 'FOM' AND p.Testperson = 0
  AND l.Produktkuerzel IN ('BBA','BBAb','BBAd','BBAn')
  AND l.Kohorte >= '2021-WS' AND l.Kohorte <= '2026-SS'
  AND l.Hochschulzentrum NOT IN ('Venlo','Sofia','Bangalore','Pune','Ahmedabad','Luxemburg')
  AND c.Gueltige_Codierung = 1
GROUP BY c.AusstiegsCluster, c.Ausstiegsstatus
ORDER BY c.AusstiegsCluster, Anzahl DESC
""")
rows2 = c.fetchall()
total2 = sum(r[2] for r in rows2 if r[0] is not None)
aktiv_reg2 = sum(r[2] for r in rows2 if r[0] == 'Eingeschrieben' and r[1] != 'V')
aktiv_v2 = sum(r[2] for r in rows2 if r[0] == 'Eingeschrieben' and r[1] == 'V')
print(f"\nMit Gueltige_Codierung=1:")
print(f"  Total (ohne NULL): {total2}")
print(f"  Aktiv regulaer: {aktiv_reg2} ({round(aktiv_reg2/total2*100,1)}%)")
print(f"  Aktiv Verlaengerung: {aktiv_v2} ({round(aktiv_v2/total2*100,1)}%)")

# Kombination: RSZ=1 + Gueltige_Codierung=1
c.execute("""
SELECT
    c.AusstiegsCluster,
    c.Ausstiegsstatus,
    COUNT(*) AS Anzahl
FROM BCW_DWH.dwh.C_StudienEin_ausstieg c
INNER JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = c.StudienEintragID
INNER JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
INNER JOIN BCW_DWH.dwh.Personen p ON p.PersonenID = se.PersonenFID
WHERE l.Institut = 'FOM' AND p.Testperson = 0
  AND l.Produktkuerzel IN ('BBA','BBAb','BBAd','BBAn')
  AND l.Kohorte >= '2021-WS' AND l.Kohorte <= '2026-SS'
  AND l.Hochschulzentrum NOT IN ('Venlo','Sofia','Bangalore','Pune','Ahmedabad','Luxemburg')
  AND c.Gueltige_Codierung = 1
  AND c.RegelstudienzeitAbgeschlossen = 1
GROUP BY c.AusstiegsCluster, c.Ausstiegsstatus
ORDER BY c.AusstiegsCluster, Anzahl DESC
""")
rows3 = c.fetchall()
total3 = sum(r[2] for r in rows3 if r[0] is not None)
aktiv_reg3 = sum(r[2] for r in rows3 if r[0] == 'Eingeschrieben' and r[1] != 'V')
aktiv_v3 = sum(r[2] for r in rows3 if r[0] == 'Eingeschrieben' and r[1] == 'V')
print(f"\nMit Gueltige_Codierung=1 UND RegelstudienzeitAbgeschlossen=1:")
print(f"  Total (ohne NULL): {total3}")
print(f"  Aktiv regulaer: {aktiv_reg3} ({round(aktiv_reg3/total3*100,1)}%)")
print(f"  Aktiv Verlaengerung: {aktiv_v3} ({round(aktiv_v3/total3*100,1)}%)")

conn.close()
