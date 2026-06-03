import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
cur = conn.cursor()

# 1. Lehrgaenge - Spalten
print("=== dwh.Lehrgaenge ===")
cur.execute("""
    SELECT COLUMN_NAME, DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA = 'dwh' AND TABLE_NAME = 'Lehrgaenge'
    ORDER BY ORDINAL_POSITION
""")
for r in cur.fetchall():
    print(f"  {r[0]} ({r[1]})")

print()

# 2. Semester table for SemesterStart
print("=== Semester-Tabellen ===")
cur.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME 
    FROM INFORMATION_SCHEMA.TABLES 
    WHERE TABLE_NAME LIKE '%Semester%'
    ORDER BY TABLE_NAME
""")
for r in cur.fetchall():
    print(f"  {r[0]}.{r[1]}")

print()

# 3. Semester Spalten
print("=== dwh.Semester (falls vorhanden) ===")
cur.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_NAME LIKE 'Semester%' AND TABLE_SCHEMA = 'dwh'
    ORDER BY TABLE_NAME, ORDINAL_POSITION
""")
for r in cur.fetchall():
    print(f"  {r[0]}.{r[1]}.{r[2]} ({r[3]})")

print()

# 4. Sample StudierendenstatusJeSemester - check Kuerzel values
print("=== StudierendenstatusJeSemester.Kuerzel (TOP 20 distinct) ===")
cur.execute("""
    SELECT DISTINCT TOP 20 Kuerzel 
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester
""")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()

# 5. StudierendenstatusJeSemester.Status - distinct values
print("=== StudierendenstatusJeSemester.Status (distinct) ===")
cur.execute("""
    SELECT DISTINCT TOP 20 Status 
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester
""")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()

# 6. StudierendenstatusJeSemester.Zustand - distinct values
print("=== StudierendenstatusJeSemester.Zustand (distinct) ===")
cur.execute("""
    SELECT DISTINCT Zustand 
    FROM BCW_DWH.dwh.StudierendenstatusJeSemester
""")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()

# 7. Check for Testperson column
print("=== Suche Testperson-Spalte ===")
cur.execute("""
    SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE COLUMN_NAME LIKE '%Testperson%' OR COLUMN_NAME LIKE '%TestPerson%'
""")
for r in cur.fetchall():
    print(f"  {r[0]}.{r[1]}.{r[2]}")

conn.close()
