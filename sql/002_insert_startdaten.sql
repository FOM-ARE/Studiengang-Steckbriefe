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
SET @bachelor = 'Bachelor';
SET @master   = 'Master';

-- Hochschulbereich-IDs (vermeiden duplizierter Literale – plsql:S1192)
SET @hsb_wm  = (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'WM');
SET @hsb_gus = (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'GuS');
SET @hsb_wp  = (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'WP');
SET @hsb_it  = (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'IT');
SET @hsb_wr  = (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'WR');
SET @hsb_ing = (SELECT Id FROM RpStudiengangSteckbriefeHochschulbereich WHERE HsbCode = 'Ing');

INSERT INTO RpStudiengangSteckbriefeStudiengang (BasisPk, Anzeigename, Abschluss, HochschulbereichId) VALUES
('BAIM',     'Angewandte Informatik (BAIM)',                         @bachelor, @hsb_it),
('BBA',      'Business Administration (BBA)',                         @bachelor, @hsb_wm),
('BGS',      'Gesundheits- und Sozialmanagement (BGS)',              @bachelor, @hsb_gus),
('BWW',      'Betriebswirtschaft & Wirtschaftspsychologie (BWW)',    @bachelor, @hsb_wp),
('BME',      'Mechatronik (BME)',                                     @bachelor, @hsb_ing),
('BMM',      'Marketing & Digitale Medien (BMM)',                    @bachelor, @hsb_wm),
('BPVP',     'Primary Care Management (BPVP)',                       @bachelor, @hsb_gus),
('BSA',      'Soziale Arbeit (BSA)',                                  @bachelor, @hsb_gus),
('BST',      'Steuerrecht (BST)',                                     @bachelor, @hsb_wr),
('BWI',      'Wirtschaftsinformatik (BWI)',                           @bachelor, @hsb_it),
('BWK',      'Wirtschaftsrecht (BWK)',                                @bachelor, @hsb_wr),
('MBA',      'Master of Business Administration (MBA)',               @master,   @hsb_wm),
('MBB',      'Business Consulting & Digital Mgmt (MBB)',             @master,   @hsb_wm),
('MME_HSBO', 'Mechatronik + HSBO (MME_HSBO)',                        @master,   @hsb_ing),
('MMT_HSBO', 'Maschinenbau + HSBO (MMT_HSBO)',                       @master,   @hsb_ing),
('MWING',    'Wirtschaftsingenieurwesen (MWING)',                     @master,   @hsb_ing);

-- ─── 4) RpStudiengangSteckbriefeProduktKuerzelAlias ──────────────────────────────
-- Studiengang-IDs (vermeiden duplizierter Literale – plsql:S1192)
SET @sg_baim  = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BAIM');
SET @sg_bba   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BBA');
SET @sg_bgs   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BGS');
SET @sg_bww   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWW');
SET @sg_bme   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BME');
SET @sg_bmm   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BMM');
SET @sg_bpvp  = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BPVP');
SET @sg_bsa   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BSA');
SET @sg_bst   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BST');
SET @sg_bwi   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWI');
SET @sg_bwk   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'BWK');
SET @sg_mba   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MBA');
SET @sg_mbb   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MBB');
SET @sg_mme   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MME_HSBO');
SET @sg_mmt   = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MMT_HSBO');
SET @sg_mwing = (SELECT Id FROM RpStudiengangSteckbriefeStudiengang WHERE BasisPk = 'MWING');

INSERT INTO RpStudiengangSteckbriefeProduktKuerzelAlias (AliasPk, StudiengangId) VALUES
('BAIM_CN',     @sg_baim),
('BBAa_Fonty',  @sg_bba),
('BBAb',        @sg_bba),
('BBAd',        @sg_bba),
('BBAv_ATA',    @sg_bba),
('BBA_AM',      @sg_bba),
('BBA_ATA',     @sg_bba),
('BBA_PM',      @sg_bba),
('BBA_AT',      @sg_bba),
('BGS_HY',      @sg_bgs),
('BHAd',        @sg_bww),
('BLOd',        @sg_bww),
('BWWa',        @sg_bww),
('BWWd',        @sg_bww),
('BMEe_INT',    @sg_bme),
('BMMq',        @sg_bmm),
('BPCM',        @sg_bpvp),
('BSAk',        @sg_bsa),
('BSTd',        @sg_bst),
('BWIK',        @sg_bwi),
('BWId',        @sg_bwi),
('BWI_BS',      @sg_bwi),
('BWKa',        @sg_bwk),
('MBAe_IN',     @sg_mba),
('MBAe_INT',    @sg_mba),
('MBBe_IN',     @sg_mbb),
('MBBe_INT',    @sg_mbb),
('MME_+_HSBO',  @sg_mme),
('MMT_+_HSBO',  @sg_mmt),
('MWING_PG',    @sg_mwing),
('MWINGe_INT',  @sg_mwing);

-- ─── 5) RpStudiengangSteckbriefeAnrechnungRegel ──────────────────────────────────

-- Regeltypen, Operatoren und Kategorien (vermeiden duplizierter Literale – plsql:S1192)
SET @rt_anrg  = 'ANRECHNUNGSGRUND';
SET @rt_la    = 'LEISTUNGSART';
SET @rt_at    = 'ANERKANNTTEXT';
SET @kat_oh   = 'OFFENE_HOCHSCHULE';
SET @kat_hs   = 'HOCHSCHULISCH';
SET @kat_berf = 'BERUFLICH';
SET @op_eq    = 'EQUALS';
SET @op_like  = 'LIKE';

-- Typ ANRECHNUNGSGRUND: Diese Werte zaehlen als "Offene Hochschule"
INSERT INTO RpStudiengangSteckbriefeAnrechnungRegel (Regeltyp, AbgleichOperator, AbgleichWert, Kategorie, Prioritaet) VALUES
(@rt_anrg, @op_eq, 'andere BW/IBW',        @kat_oh, 10),
(@rt_anrg, @op_eq, 'andere Fortbildungen', @kat_oh, 10),
(@rt_anrg, @op_eq, 'eigene BW/IBW',        @kat_oh, 10),
(@rt_anrg, @op_eq, 'eigene Ök',            @kat_oh, 10),
(@rt_anrg, @op_eq, 'Fachkaufleute',        @kat_oh, 10),
(@rt_anrg, @op_eq, 'IHK-Betriebswirt',     @kat_oh, 10),
(@rt_anrg, @op_eq, 'IHK-Fachwirt',         @kat_oh, 10);

-- Typ LEISTUNGSART: Klassifikation Hochschulisch / Beruflich
INSERT INTO RpStudiengangSteckbriefeAnrechnungRegel (Regeltyp, AbgleichOperator, AbgleichWert, Kategorie, Prioritaet) VALUES
(@rt_la, @op_like, '%Hochschulische Leistung%',       @kat_hs,   10),
(@rt_la, @op_like, '%Ausbildung%',                    @kat_berf, 20),
(@rt_la, @op_like, '%Ausserhochschulische Leistung%', @kat_berf, 20);

-- Typ ANERKANNTTEXT: Fallback-Pattern wenn keine Antraege vorhanden
INSERT INTO RpStudiengangSteckbriefeAnrechnungRegel (Regeltyp, AbgleichOperator, AbgleichWert, Kategorie, Prioritaet) VALUES
(@rt_at, @op_like, '%HS%',              @kat_hs, 10),
(@rt_at, @op_like, '%Auslandsstudium%', @kat_hs, 10),
(@rt_at, @op_like, '%ERASMUS%',         @kat_hs, 10);
-- Alles andere → BERUFLICH (Default im Code, kein Eintrag noetig)

-- ─── 6) RpStudiengangSteckbriefeEndpunktParameter ────────────────────────────────

-- Endpunkt- und Parameternamen-Konstanten (vermeiden duplizierter Literale – plsql:S1192)
SET @ep_anr  = 'anrechnungen';
SET @pn_jz   = 'jahre_zurueck';
SET @pn_kj   = 'kohorten_jahre';
SET @pn_sg   = 'statusgruppe';
SET @sg_uv   = 'Gesamtstudierende mit UV';

INSERT INTO RpStudiengangSteckbriefeEndpunktParameter (EndpunktCode, ParamName, ParamWert, Beschreibung) VALUES
('trends',              @pn_jz,             '4',            'Studierendenzahlen: Jahre zurueck'),
('stammdaten',          @pn_jz,             '2',            'Stammdaten-Zeitraum'),
('studienerfolg',       @pn_kj,             '5',            'Kohortenjahre fuer Abbrecherquote'),
('uebergang',           @pn_kj,             '5',            'Kohortenjahre fuer Uebergang B→M'),
('herkunft',            @pn_kj,             '5',            'Kohortenjahre fuer Herkunft M←B'),
('vertiefung',          'datum_von',        '2018-09-01',   'Vertiefungsrichtungen: ab Datum'),
('vertiefung',          'datum_bis',        '2021-09-01',   'Vertiefungsrichtungen: bis Datum'),
('hochschulzertifikate','datum_von',        '2021-08-01',   'Hochschulzertifikate: ab Datum'),
('zuzahler',            @pn_jz,             '4',            'Zuzahler-Zeitraum'),
(@ep_anr,               'semester_zurueck', '6',            'Anrechnungen: letzte X Semester');

-- StatusGruppen je Endpunkt
INSERT INTO RpStudiengangSteckbriefeEndpunktParameter (EndpunktCode, ParamName, ParamWert, Beschreibung) VALUES
('trends',     @pn_sg,           @sg_uv,                   'Filter fuer Studierendenzahlen'),
('stammdaten', @pn_sg,           @sg_uv,                   'Filter fuer Stammdaten'),
('zuzahler',   @pn_sg,           @sg_uv,                   'Filter fuer Zuzahler'),
(@ep_anr,      'statusgruppe_1', 'Beginner mit UV',         'Population Anrechnungen'),
(@ep_anr,      'statusgruppe_2', 'Quereinsteiger mit UV',   'Population Anrechnungen');

-- ─── 7) RpStudiengangSteckbriefeFilterliste ──────────────────────────────────────

-- Typ-Konstanten (vermeiden duplizierter Literale – plsql:S1192)
SET @incl = 'INCLUDE';
SET @excl = 'EXCLUDE';

-- HSB-Kuerzel die in der Studiengangliste ausgeschlossen werden
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ, Beschreibung) VALUES
('HSB_EXCLUDE', 'OBS',      @excl, 'Online Business School ausblenden'),
('HSB_EXCLUDE', 'eufom BS', @excl, 'eufom ausblenden'),
('HSB_EXCLUDE', '',         @excl, 'Leere HSB ausblenden');

-- Vertiefungsrichtungen: erlaubte Modulcontainer-Arten
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('VERTIEFUNG_ART', 'Vertiefungsrichtung', @incl),
('VERTIEFUNG_ART', 'Wahlpflichtmodul',   @incl),
('VERTIEFUNG_ART', 'Wahlmodul',          @incl);

-- Vertiefungsrichtungen: ausgeschlossene Fachgebiete
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('VERTIEFUNG_FACH', 'General Studies Wahlmodul ZEUGNISSE', @excl),
('VERTIEFUNG_FACH', 'Zusatzwahlfächer',                    @excl);

-- UE-Berechnung: ausgeschlossene Raum-IDs
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ, Beschreibung) VALUES
('UE_RAUMID', '274',  @excl, 'Testbuchungs-Raeume'),
('UE_RAUMID', '285',  @excl, NULL),
('UE_RAUMID', '349',  @excl, NULL),
('UE_RAUMID', '845',  @excl, NULL),
('UE_RAUMID', '1608', @excl, NULL);

-- UE-Berechnung: ausgeschlossene Veranstaltungstypen
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('UE_VERANSTTYP', 'Sonderveranstaltung', @excl);

-- UE-Berechnung: erlaubte Produktgruppen
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('UE_PRODUKTGRUPPE', 'Studium',                   @incl),
('UE_PRODUKTGRUPPE', 'Akademische Weiterbildung', @incl);

-- UE-Berechnung: StatusRPL die beruecksichtigt werden
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('UE_STATUSRPL', 'A', @incl),
('UE_STATUSRPL', 'P', @incl);

-- Zuzahler: ausgeschlossene Rechnungsempfaenger
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('ZUZAHLER_EMPF', 'Mitarbeiter', @excl);

-- Zuzahler: KostenUebernahme-Typ
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('ZUZAHLER_KOSTENTYP', 'Arbeitgeber', @incl);

-- Leistungsarten die bei Anrechnungen ignoriert werden
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('LEISTUNGSART_IGNORE', 'Einschreibehindernispruefung', @excl),
('LEISTUNGSART_IGNORE', 'Kooperation',                  @excl);

-- Duale Studierende: Studienformate die als dual gelten
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('DUAL_STUDIENFORMAT', 'ausbildungsintegrierend', @incl),
('DUAL_STUDIENFORMAT', 'berufsintegrierend',      @incl),
('DUAL_STUDIENFORMAT', 'berufsbegleitend +',      @incl);

-- Duale Studierende: Bildungsabschnitt-Bedingung
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('DUAL_BILDUNGSABSCHNITT', 'Erstausbildung', @incl);

-- Ausrichtung die global excluded wird
INSERT INTO RpStudiengangSteckbriefeFilterliste (Bereich, Wert, Typ) VALUES
('AUSRICHTUNG_EXCLUDE', 'OBS', @excl);

SELECT 'Alle Startdaten eingefuegt' AS Status;
