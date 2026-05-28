USE HochschulorgaApps;

-- ═══════════════════════════════════════════════════════════════════════════════
-- Studiengang-Steckbriefe: Startdaten fuer Konfigurations-Tabellen
-- Datenbank: HochschulorgaApps (MariaDB)
-- Server: mariadb.bcw-intern.local:3306
-- Erstellt: 2026-05-20
-- Aktualisiert: 2026-05-27 (Konventionen: PascalCase, Deutsch, Id-PKs)
-- ═══════════════════════════════════════════════════════════════════════════════
-- Hinweis: Die App liest weiterhin Nutzdaten aus dem SQL Server DWH.
--          Nur die Konfigurations-Tabellen liegen in MariaDB.
-- ═══════════════════════════════════════════════════════════════════════════════

-- ─── 1) RpStudiengangSteckbriefeHochschulbereich ─────────────────────────────────
INSERT INTO RpStudiengangSteckbriefeHochschulbereich (HsbCode, Name, Icon, FarbeHex, Sortierung) VALUES
('WM',  'Wirtschaft & Management',       '💼', '#00594D', 1),
('GuS', 'Gesundheit & Soziales',          '🏥', '#00B050', 2),
('WP',  'Wirtschaftspsychologie',         '🧠', '#8B5CF6', 3),
('IT',  'Informatik & Digitalisierung',   '💻', '#0573C1', 4),
('WR',  'Wirtschaftsrecht',               '⚖️', '#D09910', 5),
('Ing', 'Ingenieurwesen',                 '🔧', '#8FB63E', 6);

-- ─── 2) RpStudiengangSteckbriefeHochschulzentrum ─────────────────────────────────
INSERT INTO RpStudiengangSteckbriefeHochschulzentrum (Name, IstAusgeschlossen, Sortierung) VALUES
('DLS',        FALSE, 1),
('Bangalore',  TRUE,  900),
('Pune',       TRUE,  901),
('Ahmedabad',  TRUE,  902),
('Sofia',      TRUE,  903),
('Venlo',      TRUE,  904),
('Luxemburg',  TRUE,  905);

-- ─── 3) RpStudiengangSteckbriefeStudiengang ──────────────────────────────────────
INSERT INTO RpStudiengangSteckbriefeStudiengang (BasisPk, Anzeigename, Abschluss, HochschulbereichId) VALUES
('BAIM', 'Angewandte Informatik (BAIM)',       'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'IT')),
('BBA',  'Business Administration (BBA)',       'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'WM')),
('BGS',  'Gesundheits- und Sozialmanagement (BGS)', 'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'GuS')),
('BWW',  'Betriebswirtschaft & Wirtschaftspsychologie (BWW)', 'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'WP')),
('BME',  'Mechatronik (BME)',                   'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'Ing')),
('BMM',  'Marketing & Digitale Medien (BMM)',   'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'WM')),
('BPVP', 'Primary Care Management (BPVP)',      'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'GuS')),
('BSA',  'Soziale Arbeit (BSA)',                'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'GuS')),
('BST',  'Steuerrecht (BST)',                   'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'WR')),
('BWI',  'Wirtschaftsinformatik (BWI)',         'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'IT')),
('BWK',  'Wirtschaftsrecht (BWK)',              'Bachelor', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'WR')),
('MBA',  'Master of Business Administration (MBA)', 'Master', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'WM')),
('MBB',  'Business Consulting & Digital Mgmt (MBB)', 'Master', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'WM')),
('MME_HSBO', 'Mechatronik + HSBO (MME_HSBO)',   'Master', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'Ing')),
('MMT_HSBO', 'Maschinenbau + HSBO (MMT_HSBO)',  'Master', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'Ing')),
('MWING', 'Wirtschaftsingenieurwesen (MWING)',  'Master', (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'Ing'));

-- ─── 4) RpStudiengangSteckbriefeProduktKuerzelAlias ──────────────────────────────
INSERT INTO RpStudiengangSteckbriefeProduktKuerzelAlias (AliasPk, StudiengangId) VALUES
('BAIM_CN',     (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BAIM')),
('BBAa_Fonty',  (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BBA')),
('BBAb',        (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BBA')),
('BBAd',        (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BBA')),
('BBAv_ATA',    (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BBA')),
('BBA_AM',      (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BBA')),
('BBA_ATA',     (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BBA')),
('BBA_PM',      (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BBA')),
('BBA_AT',      (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BBA')),
('BGS_HY',     (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BGS')),
('BHAd',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWW')),
('BLOd',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWW')),
('BWWa',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWW')),
('BWWd',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWW')),
('BMEe_INT',   (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BME')),
('BMMq',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BMM')),
('BPCM',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BPVP')),
('BSAk',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BSA')),
('BSTd',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BST')),
('BWIK',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWI')),
('BWId',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWI')),
('BWI_BS',     (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWI')),
('BWKa',       (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWK')),
('MBAe_IN',    (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MBA')),
('MBAe_INT',   (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MBA')),
('MBBe_IN',    (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MBB')),
('MBBe_INT',   (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MBB')),
('MME_+_HSBO', (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MME_HSBO')),
('MMT_+_HSBO', (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MMT_HSBO')),
('MWING_PG',   (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MWING')),
('MWINGe_INT', (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MWING'));

-- ─── 5) RpStudiengangSteckbriefeAnrechnungRegel ──────────────────────────────────

-- Typ ANRECHNUNGSGRUND: Diese Werte zaehlen als "Offene Hochschule"
INSERT INTO RpStudiengangSteckbriefeAnrechnungRegel (Regeltyp, AbgleichOperator, AbgleichWert, Kategorie, Prioritaet) VALUES
('ANRECHNUNGSGRUND', 'EQUALS', 'andere BW/IBW',          'OFFENE_HOCHSCHULE', 10),
('ANRECHNUNGSGRUND', 'EQUALS', 'andere Fortbildungen',   'OFFENE_HOCHSCHULE', 10),
('ANRECHNUNGSGRUND', 'EQUALS', 'eigene BW/IBW',          'OFFENE_HOCHSCHULE', 10),
('ANRECHNUNGSGRUND', 'EQUALS', 'eigene Ök',              'OFFENE_HOCHSCHULE', 10),
('ANRECHNUNGSGRUND', 'EQUALS', 'Fachkaufleute',          'OFFENE_HOCHSCHULE', 10),
('ANRECHNUNGSGRUND', 'EQUALS', 'IHK-Betriebswirt',       'OFFENE_HOCHSCHULE', 10),
('ANRECHNUNGSGRUND', 'EQUALS', 'IHK-Fachwirt',           'OFFENE_HOCHSCHULE', 10);

-- Typ LEISTUNGSART: Klassifikation Hochschulisch / Beruflich
INSERT INTO RpStudiengangSteckbriefeAnrechnungRegel (Regeltyp, AbgleichOperator, AbgleichWert, Kategorie, Prioritaet) VALUES
('LEISTUNGSART', 'LIKE', '%Hochschulische Leistung%',            'HOCHSCHULISCH', 10),
('LEISTUNGSART', 'LIKE', '%Ausbildung%',                         'BERUFLICH',     20),
('LEISTUNGSART', 'LIKE', '%Ausserhochschulische Leistung%',      'BERUFLICH',     20);

-- Typ ANERKANNTTEXT: Fallback-Pattern wenn keine Antraege vorhanden
INSERT INTO RpStudiengangSteckbriefeAnrechnungRegel (Regeltyp, AbgleichOperator, AbgleichWert, Kategorie, Prioritaet) VALUES
('ANERKANNTTEXT', 'LIKE', '%HS%',              'HOCHSCHULISCH', 10),
('ANERKANNTTEXT', 'LIKE', '%Auslandsstudium%', 'HOCHSCHULISCH', 10),
('ANERKANNTTEXT', 'LIKE', '%ERASMUS%',         'HOCHSCHULISCH', 10);
-- Alles andere → BERUFLICH (Default im Code, kein Eintrag noetig)

-- ─── 6) RpStudiengangSteckbriefeEndpunktParameter ────────────────────────────────

INSERT INTO RpStudiengangSteckbriefeEndpunktParameter (EndpunktCode, ParamName, ParamWert, Beschreibung) VALUES
('trends',              'jahre_zurueck',        '4',            'Studierendenzahlen: Jahre zurueck'),
('stammdaten',          'jahre_zurueck',        '2',            'Stammdaten-Zeitraum'),
('studienerfolg',       'kohorten_jahre',       '5',            'Kohortenjahre fuer Abbrecherquote'),
('uebergang',           'kohorten_jahre',       '5',            'Kohortenjahre fuer Uebergang B→M'),
('herkunft',            'kohorten_jahre',       '5',            'Kohortenjahre fuer Herkunft M←B'),
('vertiefung',          'datum_von',            '2018-09-01',   'Vertiefungsrichtungen: ab Datum'),
('vertiefung',          'datum_bis',            '2021-09-01',   'Vertiefungsrichtungen: bis Datum'),
('hochschulzertifikate','datum_von',            '2021-08-01',   'Hochschulzertifikate: ab Datum'),
('zuzahler',            'jahre_zurueck',        '4',            'Zuzahler-Zeitraum'),
('anrechnungen',        'semester_zurueck',     '6',            'Anrechnungen: letzte X Semester');

-- StatusGruppen je Endpunkt
INSERT INTO RpStudiengangSteckbriefeEndpunktParameter (EndpunktCode, ParamName, ParamWert, Beschreibung) VALUES
('trends',         'statusgruppe',      'Gesamtstudierende mit UV',  'Filter fuer Studierendenzahlen'),
('stammdaten',     'statusgruppe',      'Gesamtstudierende mit UV',  'Filter fuer Stammdaten'),
('zuzahler',       'statusgruppe',      'Gesamtstudierende mit UV',  'Filter fuer Zuzahler'),
('anrechnungen',   'statusgruppe_1',    'Beginner mit UV',           'Population Anrechnungen'),
('anrechnungen',   'statusgruppe_2',    'Quereinsteiger mit UV',     'Population Anrechnungen');

-- ─── 7) RpStudiengangSteckbriefeFilterliste ──────────────────────────────────────

-- HSB-Kuerzel die in der Studiengangliste ausgeschlossen werden
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ, Beschreibung) VALUES
('HSB_EXCLUDE',       'OBS',         'EXCLUDE', 'Online Business School ausblenden'),
('HSB_EXCLUDE',       'eufom BS',    'EXCLUDE', 'eufom ausblenden'),
('HSB_EXCLUDE',       '',            'EXCLUDE', 'Leere HSB ausblenden');

-- Vertiefungsrichtungen: erlaubte Modulcontainer-Arten
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('VERTIEFUNG_ART',    'Vertiefungsrichtung',  'INCLUDE'),
('VERTIEFUNG_ART',    'Wahlpflichtmodul',     'INCLUDE'),
('VERTIEFUNG_ART',    'Wahlmodul',            'INCLUDE');

-- Vertiefungsrichtungen: ausgeschlossene Fachgebiete
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('VERTIEFUNG_FACH',   'General Studies Wahlmodul ZEUGNISSE', 'EXCLUDE'),
('VERTIEFUNG_FACH',   'Zusatzwahlfächer',                    'EXCLUDE');

-- UE-Berechnung: ausgeschlossene Raum-IDs
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ, Beschreibung) VALUES
('UE_RAUMID',         '274',   'EXCLUDE', 'Testbuchungs-Raeume'),
('UE_RAUMID',         '285',   'EXCLUDE', NULL),
('UE_RAUMID',         '349',   'EXCLUDE', NULL),
('UE_RAUMID',         '845',   'EXCLUDE', NULL),
('UE_RAUMID',         '1608',  'EXCLUDE', NULL);

-- UE-Berechnung: ausgeschlossene Veranstaltungstypen
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('UE_VERANSTTYP',     'Sonderveranstaltung',  'EXCLUDE');

-- UE-Berechnung: erlaubte Produktgruppen
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('UE_PRODUKTGRUPPE',  'Studium',                      'INCLUDE'),
('UE_PRODUKTGRUPPE',  'Akademische Weiterbildung',    'INCLUDE');

-- UE-Berechnung: StatusRPL die beruecksichtigt werden
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('UE_STATUSRPL',      'A',  'INCLUDE'),
('UE_STATUSRPL',      'P',  'INCLUDE');

-- Zuzahler: ausgeschlossene Rechnungsempfaenger
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('ZUZAHLER_EMPF',     'Mitarbeiter',  'EXCLUDE');

-- Zuzahler: KostenUebernahme-Typ
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('ZUZAHLER_KOSTENTYP', 'Arbeitgeber', 'INCLUDE');

-- Leistungsarten die bei Anrechnungen ignoriert werden
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('LEISTUNGSART_IGNORE', 'Einschreibehindernispruefung', 'EXCLUDE'),
('LEISTUNGSART_IGNORE', 'Kooperation',                  'EXCLUDE');

-- Duale Studierende: Studienformate die als dual gelten
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('DUAL_STUDIENFORMAT', 'ausbildungsintegrierend', 'INCLUDE'),
('DUAL_STUDIENFORMAT', 'berufsintegrierend',      'INCLUDE'),
('DUAL_STUDIENFORMAT', 'berufsbegleitend +',      'INCLUDE');

-- Duale Studierende: Bildungsabschnitt-Bedingung
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('DUAL_BILDUNGSABSCHNITT', 'Erstausbildung', 'INCLUDE');

-- Ausrichtung die global excluded wird
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('AUSRICHTUNG_EXCLUDE', 'OBS', 'EXCLUDE');

SELECT 'Alle Startdaten eingefuegt' AS Status;
