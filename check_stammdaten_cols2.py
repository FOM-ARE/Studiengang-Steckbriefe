import pyodbc

conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
cur = conn.cursor()

# 1. Personen Staatsangehoerigkeit Werte
print("=== dwh.Personen - Staatsangehoerigkeit (sample) ===")
cur.execute("""
    SELECT TOP 20 Staatsangehoerigkeit, COUNT(*) as cnt 
    FROM BCW_DWH.dwh.Personen 
    GROUP BY Staatsangehoerigkeit 
    ORDER BY cnt DESC
""")
for r in cur.fetchall():
    print(f"  '{r[0]}' ({r[1]})")

print()

# 2. Check if Lehrgaenge has something like "Erstausbildung" / "Weiterbildung"
print("=== dwh.Lehrgaenge - Alle Spalten ===")
cur.execute("""
    SELECT COLUMN_NAME 
    FROM INFORMATION_SCHEMA.COLUMNS 
    WHERE TABLE_SCHEMA='dwh' AND TABLE_NAME='Lehrgaenge'
    ORDER BY ORDINAL_POSITION
""")
for r in cur.fetchall():
    print(f"  {r[0]}")

print()

# 3. Check HochschulWelt as potential Bildungsabschnitt proxy
print("=== dwh.Lehrgaenge - HochschulWelt (sample) ===")
cur.execute("SELECT DISTINCT HochschulWelt FROM BCW_DWH.dwh.Lehrgaenge WHERE Institut='FOM'")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()

# 4. Vergleich: holy DualerStudiengang vs Bildungsabschnitt-Logik
# Prüfe ob DualerStudiengang='Y' äquivalent ist zur Bildungsabschnitt-Logik
print("=== Lehrgaenge DualerStudiengang='Y' Beispiele ===")
cur.execute("""
    SELECT TOP 10 Lehrgangskuerzel, DualerStudiengang, Produktart, ZeitmodellDetail, Ausrichtung
    FROM BCW_DWH.dwh.Lehrgaenge 
    WHERE Institut='FOM' AND DualerStudiengang='Y'
""")
for r in cur.fetchall():
    print(f"  {r[0]} | dual={r[1]} | art={r[2]} | zeit={r[3]} | ausricht={r[4]}")

print()

# 5. Wie ist Zeitmodell im DWH? 'Tages-Studium' vs 'Tagesstudium'
print("=== Lehrgaenge mit 'Tages' in ZeitmodellDetail ===")
cur.execute("""
    SELECT DISTINCT ZeitmodellDetail 
    FROM BCW_DWH.dwh.Lehrgaenge 
    WHERE Institut='FOM' AND ZeitmodellDetail LIKE '%Tages%'
""")
for r in cur.fetchall():
    print(f"  '{r[0]}'")

print()

# 6. Check Lehrgaenge.LehrgangsStart vs sta_l.DauerVon
print("=== LehrgangsStart Beispiel für BBA WS16 CN-TY ===")
cur.execute("""
    SELECT LehrgangsID, Lehrgangskuerzel, LehrgangsStart, LehrgangsEnde
    FROM BCW_DWH.dwh.Lehrgaenge 
    WHERE Lehrgangskuerzel = 'BBA WS16 CN-TY'
""")
for r in cur.fetchall():
    print(f"  ID={r[0]} | Kuerzel={r[1]} | Start={r[2]} | Ende={r[3]}")

print()

# 7. AnrechnungsGrund Werte für Offene Hochschule
print("=== StudienEintraege.AnrechnungsGrund (sample) ===")
cur.execute("""
    SELECT TOP 20 AnrechnungsGrund, COUNT(*) as cnt
    FROM BCW_DWH.dwh.StudienEintraege
    WHERE AnrechnungsGrund IS NOT NULL AND AnrechnungsGrund <> ''
    GROUP BY AnrechnungsGrund
    ORDER BY cnt DESC
""")
for r in cur.fetchall():
    print(f"  '{r[0]}' ({r[1]})")

conn.close()
