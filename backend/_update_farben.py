import ssl, pymysql, time

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

# Farbzuordnungen aus Excel "Farbwelten Ressort, HSB, Institut für VSC.xlsx"
updates = [
    ('WM', '#00534A'),   # Wirtschaft & Management
    ('WP', '#D04931'),   # Wirtschaftspsychologie (Excel: "Wirtschaft & Psychologie")
    ('IT', '#00B3F0'),   # Informatik & Digitalisierung (Excel: "IT-Management")
    ('GuS', '#6B1B4B'),  # Gesundheit & Soziales
    ('Ing', '#007C91'),  # Ingenieurwesen
    # WR bleibt gleich: #D09910
]

for code, farbe in updates:
    for attempt in range(3):
        try:
            conn = pymysql.connect(
                host='mariadb.bcw-intern.local',
                port=3306,
                user='HochschulorgaApps',
                password='%z8J9xjZha)9,)Jn',
                database='HochschulorgaApps',
                charset='utf8mb4',
                ssl=ssl_ctx
            )
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE Rp_Studiengang_Steckbriefe_hochschulbereich SET farbe_hex = %s WHERE hsb_code = %s",
                    (farbe, code)
                )
                conn.commit()
                print(f'{code}: -> {farbe} OK')
            conn.close()
            break
        except Exception as e:
            print(f'{code}: Versuch {attempt+1} fehlgeschlagen: {e}')
            time.sleep(2)
    else:
        print(f'{code}: FEHLER nach 3 Versuchen!')

print('\nFertig!')
