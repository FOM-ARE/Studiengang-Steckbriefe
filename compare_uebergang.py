"""Vergleich: data.csv PersonenIDs vs. App-Query SQL_UEBERGANG für BBA."""

import csv

import pyodbc

# 1) PersonenIDs aus data.csv laden
csv_path = r"j:\Bw\2_Reports\02_Academic Analytics\2026_05_19_ARE_Felten_aktive_POs\data.csv"
with open(csv_path, encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    excel_ids = set(int(r["PersonenID"].strip()) for r in reader)
print(f"data.csv: {len(excel_ids)} PersonenIDs")

# 2) App-Query ausführen (identisch mit SQL_UEBERGANG für BBA)
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=ms-sql-107.bcw-intern.local,1433;"
    "DATABASE=BCW_DWH;"
    "Trusted_Connection=yes;"
)
cursor = conn.cursor()

sql = """
    WITH bachelor_absolventen AS (
        SELECT
            se_b.PersonenFID,
            l_b.Produktkuerzel AS B_PK,
            l_b.Kohorte AS B_Kohorte
        FROM BCW_DWH.dwh.StudienEintraege se_b
            INNER JOIN BCW_DWH.dwh.Lehrgaenge l_b ON l_b.LehrgangsID = se_b.LehrgangsFID
            INNER JOIN BCW_DWH.dwh.Personen p_b ON p_b.PersonenID = se_b.PersonenFID
            LEFT JOIN BCW_DWH.dwh.C_StudienEin_ausstieg c_b ON c_b.StudienEintragID = se_b.StudienEintragID
        WHERE l_b.Institut = 'FOM'
          AND p_b.Testperson = 0
          AND l_b.Produktkuerzel IN ('BBA','BBAb','BBAd','BBAn')
          AND l_b.Produktart LIKE 'Bachelor%'
          AND (
              (c_b.Ausstiegsstatus = 'A' AND c_b.Gueltige_Codierung = 1)
              OR (c_b.StudienEintragID IS NULL AND se_b.Exmatrikulationsgrund LIKE '1 %')
          )
          AND se_b.AbschlussNote > 0.1
          AND se_b.ImmatrikulationsDatum < se_b.ExmatrikulationsDatum
          AND l_b.LehrgangsEnde < GETDATE()
          AND l_b.Kohorte >= CONCAT(CAST(YEAR(DATEADD(YEAR, -5, GETDATE())) AS VARCHAR), '-WS')
          AND l_b.Hochschulzentrum NOT IN ('Bangalore','Pune','Ahmedabad','Sofia','Venlo','Luxemburg')
    )
    SELECT DISTINCT PersonenFID FROM bachelor_absolventen
"""
cursor.execute(sql)
app_ids = set(row[0] for row in cursor.fetchall())
print(f"App-Query: {len(app_ids)} PersonenIDs")

# 3) Vergleich
in_excel_not_app = excel_ids - app_ids
in_app_not_excel = app_ids - excel_ids
in_both = excel_ids & app_ids

print(f"\nIn BEIDEN: {len(in_both)}")
print(f"In data.csv, NICHT in App: {len(in_excel_not_app)}")
print(f"In App, NICHT in data.csv: {len(in_app_not_excel)}")

# 4) Warum fehlen die in der App? Details abfragen
if in_excel_not_app:
    placeholders = ",".join(str(i) for i in list(in_excel_not_app)[:200])
    detail_sql = f"""
        SELECT 
            se_b.PersonenFID,
            l_b.Kohorte,
            l_b.Hochschulzentrum,
            l_b.LehrgangsEnde,
            se_b.AbschlussNote,
            se_b.Exmatrikulationsgrund,
            c_b.Ausstiegsstatus,
            c_b.Gueltige_Codierung,
            CASE WHEN c_b.StudienEintragID IS NULL THEN 1 ELSE 0 END AS Kein_C_Eintrag
        FROM BCW_DWH.dwh.StudienEintraege se_b
            INNER JOIN BCW_DWH.dwh.Lehrgaenge l_b ON l_b.LehrgangsID = se_b.LehrgangsFID
            LEFT JOIN BCW_DWH.dwh.C_StudienEin_ausstieg c_b ON c_b.StudienEintragID = se_b.StudienEintragID
        WHERE l_b.Institut = 'FOM'
          AND l_b.Produktkuerzel IN ('BBA','BBAb','BBAd','BBAn')
          AND l_b.Produktart LIKE 'Bachelor%'
          AND se_b.PersonenFID IN ({placeholders})
          AND se_b.ImmatrikulationsDatum < se_b.ExmatrikulationsDatum
          AND l_b.Kohorte >= '2021-WS'
    """
    cursor.execute(detail_sql)
    cols = [c[0] for c in cursor.description]
    rows = [dict(zip(cols, row, strict=False)) for row in cursor.fetchall()]

    # Gründe zusammenfassen
    reasons = {
        "Gueltige_Codierung != 1": 0,
        "AbschlussNote <= 0.1 oder NULL": 0,
        "LehrgangsEnde >= GETDATE()": 0,
        "Kein Absolvent (Ausstiegsstatus != A)": 0,
        "Kein C_StudienEin_ausstieg + Exmatgrund != 1%": 0,
    }
    from datetime import datetime

    now = datetime.now()

    for r in rows:
        if r["Ausstiegsstatus"] == "A" and r["Gueltige_Codierung"] != 1:
            reasons["Gueltige_Codierung != 1"] += 1
        elif r["Ausstiegsstatus"] != "A" and not r["Kein_C_Eintrag"]:
            reasons["Kein Absolvent (Ausstiegsstatus != A)"] += 1
        elif r["Kein_C_Eintrag"] and (
            not r["Exmatrikulationsgrund"] or not str(r["Exmatrikulationsgrund"]).startswith("1 ")
        ):
            reasons["Kein C_StudienEin_ausstieg + Exmatgrund != 1%"] += 1
        elif r["AbschlussNote"] is None or float(r["AbschlussNote"]) <= 0.1:
            reasons["AbschlussNote <= 0.1 oder NULL"] += 1
        elif r["LehrgangsEnde"] and r["LehrgangsEnde"] >= now:
            reasons["LehrgangsEnde >= GETDATE()"] += 1
        else:
            reasons.setdefault("Sonstiges", 0)
            reasons["Sonstiges"] = reasons.get("Sonstiges", 0) + 1

    print("\n--- Gründe warum in data.csv aber NICHT in App ---")
    for reason, cnt in sorted(reasons.items(), key=lambda x: -x[1]):
        if cnt > 0:
            print(f"  {reason}: {cnt}")

conn.close()
