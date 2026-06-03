import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};SERVER=ms-sql-107.bcw-intern.local,1433;DATABASE=BCW_DWH;Trusted_Connection=yes"
)
cur = conn.cursor()

# Check: gibt es BBA_CN als eigenes Produktkuerzel oder ist es in BBA enthalten?
print("=== Produktkuerzel mit 'BBA' ===")
cur.execute("""
    SELECT l.Produktkuerzel, COUNT(DISTINCT se.StudienEintragID) as Cnt
    FROM BCW_DWH.dwh.Lehrgaenge l
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.LehrgangsFID = l.LehrgangsID
    WHERE l.Produktkuerzel LIKE 'BBA%'
      AND l.Institut = 'FOM'
      AND l.Kohorte >= '2021-WS' AND l.Kohorte <= '2026-SS'
    GROUP BY l.Produktkuerzel
    ORDER BY l.Produktkuerzel
""")
for row in cur.fetchall():
    print(f"  {row[0]:15s}  {row[1]:6d}")

# Check: BBA mit Kooperationsname
print("\n=== BBA nach Kooperationsname (Top 10) ===")
cur.execute("""
    SELECT l.Kooperationsname, COUNT(DISTINCT se.StudienEintragID) as Cnt
    FROM BCW_DWH.dwh.Lehrgaenge l
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.LehrgangsFID = l.LehrgangsID
    WHERE l.Produktkuerzel = 'BBA'
      AND l.Institut = 'FOM'
      AND l.Kohorte >= '2021-WS' AND l.Kohorte <= '2026-SS'
    GROUP BY l.Kooperationsname
    ORDER BY Cnt DESC
""")
for row in cur.fetchall():
    print(f"  {str(row[0]):30s}  {row[1]:6d}")

# Check: BBA nach Franchising
print("\n=== BBA nach Franchising ===")
cur.execute("""
    SELECT l.Franchising, COUNT(DISTINCT se.StudienEintragID) as Cnt
    FROM BCW_DWH.dwh.Lehrgaenge l
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.LehrgangsFID = l.LehrgangsID
    WHERE l.Produktkuerzel = 'BBA'
      AND l.Institut = 'FOM'
      AND l.Kohorte >= '2021-WS' AND l.Kohorte <= '2026-SS'
    GROUP BY l.Franchising
    ORDER BY Cnt DESC
""")
for row in cur.fetchall():
    print(f"  {str(row[0]):15s}  {row[1]:6d}")

conn.close()
