import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
cur = conn.cursor()

# Check: how many semesters have Zustand='1' per StudienEintragFID?
print("=== Zustand='1' rows per StudienEintragFID (BBA 2023-WS, sample) ===")
cur.execute("""
    SELECT TOP 10 sjs.StudienEintragFID, COUNT(*) as cnt_z1,
        (SELECT COUNT(*) FROM BCW_DWH.dwh.StudierendenstatusJeSemester x WHERE x.StudienEintragFID = sjs.StudienEintragFID) as cnt_all
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sjs.StudienEintragFID
    JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
    WHERE l.Produktkuerzel = 'BBA' AND l.Kohorte = '2023-WS' AND sjs.Zustand = '1'
    GROUP BY sjs.StudienEintragFID
    ORDER BY cnt_z1 DESC
""")
for r in cur.fetchall():
    print(f"  ID={r[0]}: Zustand=1 in {r[1]} Semestern (von {r[2]} total)")

print()

# For a specific student with Zustand=1 in multiple semesters, show all rows
print("=== Detail: erster Student mit mehreren Zustand=1 ===")
cur.execute("""
    SELECT TOP 1 sjs.StudienEintragFID
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sjs.StudienEintragFID
    JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
    WHERE l.Produktkuerzel = 'BBA' AND l.Kohorte = '2023-WS' AND sjs.Zustand = '1'
    GROUP BY sjs.StudienEintragFID
    HAVING COUNT(*) > 1
    ORDER BY COUNT(*) DESC
""")
sample_id = cur.fetchone()[0]
print(f"  StudienEintragFID = {sample_id}")
cur.execute("""
    SELECT sjs.Zustand, sjs.Status, sjs.Fachsemester, sem.SemesterKuerzel, sem.SemesterStart
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
    JOIN BCW_DWH.dwh.Semester sem ON sem.SemesterID = sjs.SemesterID
    WHERE sjs.StudienEintragFID = ?
    ORDER BY sem.SemesterStart
""", sample_id)
for r in cur.fetchall():
    print(f"  Zustand={r[0]}, Status={r[1]:<40}, FS={r[2]}, Sem={r[3]}, Start={r[4]}")

print()

# Also check a dropped student
print("=== Detail: Abbrecher (Zustand=1, Status like '%Abbrecher%') ===")
cur.execute("""
    SELECT TOP 1 sjs.StudienEintragFID
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sjs.StudienEintragFID
    JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
    WHERE l.Produktkuerzel = 'BBA' AND l.Kohorte = '2023-WS' 
      AND sjs.Status LIKE '%Abbrecher%' AND sjs.Zustand = '1'
""")
sample_id2 = cur.fetchone()[0]
print(f"  StudienEintragFID = {sample_id2}")
cur.execute("""
    SELECT sjs.Zustand, sjs.Status, sjs.Fachsemester, sem.SemesterKuerzel, sem.SemesterStart
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
    JOIN BCW_DWH.dwh.Semester sem ON sem.SemesterID = sjs.SemesterID
    WHERE sjs.StudienEintragFID = ?
    ORDER BY sem.SemesterStart
""", sample_id2)
for r in cur.fetchall():
    print(f"  Zustand={r[0]}, Status={r[1]:<40}, FS={r[2]}, Sem={r[3]}, Start={r[4]}")

conn.close()
