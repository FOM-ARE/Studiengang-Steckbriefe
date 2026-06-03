import pyodbc

conn = pyodbc.connect(
    "DRIVER={SQL Server};SERVER=ms-sql-107.bcw-intern.local,1433;DATABASE=BCW_DWH;Trusted_Connection=yes"
)
cur = conn.cursor()

# Was ist Gueltige_Codierung? Werte und Verteilung
cur.execute("""
    SELECT Gueltige_Codierung, COUNT(*) AS Anzahl
    FROM BCW_DWH.dwh.C_StudienEin_ausstieg
    WHERE Institut = 'FOM' AND Produktkuerzel = 'BBA'
      AND Kohorte >= '2021-WS'
    GROUP BY Gueltige_Codierung
    ORDER BY Gueltige_Codierung
""")
print("Gueltige_Codierung - Verteilung (BBA, Kohorte >= 2021-WS):")
for row in cur.fetchall():
    print(f"  Wert={row[0]}: {row[1]} Datensaetze")

print()

# Was unterscheidet Gueltige_Codierung = 0 von 1?
cur.execute("""
    SELECT TOP 20 
        Gueltige_Codierung, AusstiegsCluster, Ausstiegsstatus,
        COUNT(*) AS Anzahl
    FROM BCW_DWH.dwh.C_StudienEin_ausstieg
    WHERE Institut = 'FOM' AND Produktkuerzel = 'BBA'
      AND Kohorte >= '2021-WS'
    GROUP BY Gueltige_Codierung, AusstiegsCluster, Ausstiegsstatus
    ORDER BY Gueltige_Codierung, Anzahl DESC
""")
print("Gueltige_Codierung vs AusstiegsCluster vs Ausstiegsstatus:")
header = f"{'GC':>3} {'AusstiegsCluster':<25} {'Ausstiegsstatus':<20} {'Anzahl':>8}"
print(header)
print("-" * 65)
for row in cur.fetchall():
    line = f"{row[0]:>3} {str(row[1]):<25} {str(row[2]):<20} {row[3]:>8}"
    print(line)

print()
# Beispiele fuer ungueltige Codierung
cur.execute("""
    SELECT TOP 10
        Produktkuerzel, Kohorte, AusstiegsCluster, Ausstiegsstatus,
        AktuellesFachsemester, RegelstudienzeitAbgeschlossen
    FROM BCW_DWH.dwh.C_StudienEin_ausstieg
    WHERE Institut = 'FOM' AND Produktkuerzel = 'BBA'
      AND Kohorte >= '2021-WS'
      AND Gueltige_Codierung = 0
""")
print("Beispiele fuer Gueltige_Codierung = 0:")
for row in cur.fetchall():
    print(
        f"  {row[0]} | Kohorte={row[1]} | Cluster={row[2]} | Status={row[3]} | FS={row[4]} | RSZ={row[5]}"
    )

conn.close()
