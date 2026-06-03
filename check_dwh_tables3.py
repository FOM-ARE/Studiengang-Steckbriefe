import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
cur = conn.cursor()

# 1. Personen table
print("=== dwh.Personen ===")
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'Personen'
    ORDER BY ORDINAL_POSITION
""")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

print()

# 2. ALL distinct Status values from StudierendenstatusJeSemester
print("=== ALL Status values in StudierendenstatusJeSemester ===")
cur.execute("""
    SELECT DISTINCT Status 
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester
    ORDER BY Status
""")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()

# 3. Sample join: StatusJeSemester + StudienEintraege + Lehrgaenge for BBA
print("=== Sample BBA join (5 rows) ===")
cur.execute("""
    SELECT TOP 5
        sjs.Zustand, sjs.Status, sjs.Fachsemester, sjs.Kuerzel,
        se.ImmatrikulationsDatum, se.ExmatrikulationsDatum, se.Exmatrikulationsgrund,
        l.Produktkuerzel, l.Kohorte, l.LehrgangsEnde, l.Hochschulzentrum,
        sem.SemesterKuerzel, sem.SemesterStart
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sjs.StudienEintragFID
    JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
    JOIN BCW_DWH.dwh.Semester sem ON sem.SemesterID = sjs.SemesterID
    WHERE l.Produktkuerzel = 'BBA' AND l.Kohorte = '2023-WS'
      AND sjs.Zustand = '1'
""")
for r in cur.fetchall():
    print(f"  Zustand={r[0]}, Status={r[1]}, FS={r[2]}, Kuerzel={r[3]}")
    print(f"    Imma={r[4]}, Exma={r[5]}, ExmaGrund={r[6]}")
    print(f"    PK={r[7]}, Kohorte={r[8]}, LGEnde={r[9]}, HSZ={r[10]}")
    print(f"    Sem={r[11]}, SemStart={r[12]}")
    print()

# 4. How many semesters per student? (to understand: is this one row per student per semester?)
print("=== Rows per StudienEintrag (sample BBA 2023-WS) ===")
cur.execute("""
    SELECT TOP 10 sjs.StudienEintragFID, COUNT(*) as cnt
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester sjs
    JOIN BCW_DWH.dwh.StudienEintraege se ON se.StudienEintragID = sjs.StudienEintragFID
    JOIN BCW_DWH.dwh.Lehrgaenge l ON l.LehrgangsID = se.LehrgangsFID
    WHERE l.Produktkuerzel = 'BBA' AND l.Kohorte = '2023-WS'
    GROUP BY sjs.StudienEintragFID
    ORDER BY cnt DESC
""")
for r in cur.fetchall():
    print(f"  StudienEintragFID={r[0]}: {r[1]} Semester-Einträge")

conn.close()
