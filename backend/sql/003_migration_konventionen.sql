-- ═══════════════════════════════════════════════════════════════════════════════
-- Migration: Tabellen- und Spaltennamen auf DB-Konventionen anpassen
-- Datenbank: HochschulorgaApps (MariaDB)
-- Erstellt: 2026-05-27
-- ═══════════════════════════════════════════════════════════════════════════════
-- Aenderungen:
--   - Tabellennamen: snake_case → PascalCase
--   - Spaltennamen: snake_case → PascalCase, Deutsch, Boolean mit Ist-Praefix
--   - Primaerschluessel: textbasiert → Id INT AUTO_INCREMENT
--   - Fremdschluessel: [Tabelle]Id statt Textverweise
-- ═══════════════════════════════════════════════════════════════════════════════

USE HochschulorgaApps;

-- ─── Fremdschluessel-Constraints vorab entfernen ─────────────────────────────
ALTER TABLE Rp_Studiengang_Steckbriefe_studiengang
    DROP FOREIGN KEY FK_Rp_SG_Steckbriefe_studiengang_hsb;

ALTER TABLE Rp_Studiengang_Steckbriefe_produktkuerzel_alias
    DROP FOREIGN KEY FK_Rp_SG_Steckbriefe_pkalias_sg;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 1) Hochschulbereich
-- ═══════════════════════════════════════════════════════════════════════════════
ALTER TABLE Rp_Studiengang_Steckbriefe_hochschulbereich
    ADD COLUMN Id INT NOT NULL AUTO_INCREMENT FIRST,
    DROP PRIMARY KEY,
    ADD PRIMARY KEY (Id),
    ADD UNIQUE (hsb_code);

ALTER TABLE Rp_Studiengang_Steckbriefe_hochschulbereich
    CHANGE COLUMN hsb_code HsbCode VARCHAR(20) NOT NULL,
    CHANGE COLUMN hsb_name Name VARCHAR(120) NOT NULL,
    CHANGE COLUMN icon Icon VARCHAR(10) NOT NULL DEFAULT '📚',
    CHANGE COLUMN farbe_hex FarbeHex CHAR(7) NOT NULL DEFAULT '#607D8B',
    CHANGE COLUMN sort_order Sortierung INT NOT NULL DEFAULT 99,
    CHANGE COLUMN aktiv IstAktiv BOOLEAN NOT NULL DEFAULT TRUE;

RENAME TABLE Rp_Studiengang_Steckbriefe_hochschulbereich
    TO RpStudiengangSteckbriefeHochschulbereich;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 2) Hochschulzentrum
-- ═══════════════════════════════════════════════════════════════════════════════
ALTER TABLE Rp_Studiengang_Steckbriefe_hochschulzentrum
    ADD COLUMN Id INT NOT NULL AUTO_INCREMENT FIRST,
    DROP PRIMARY KEY,
    ADD PRIMARY KEY (Id),
    ADD UNIQUE (hsz_name);

ALTER TABLE Rp_Studiengang_Steckbriefe_hochschulzentrum
    CHANGE COLUMN hsz_name Name VARCHAR(120) NOT NULL,
    CHANGE COLUMN ist_excluded IstAusgeschlossen BOOLEAN NOT NULL DEFAULT FALSE,
    CHANGE COLUMN sort_order Sortierung INT NOT NULL DEFAULT 100,
    CHANGE COLUMN aktiv IstAktiv BOOLEAN NOT NULL DEFAULT TRUE;

RENAME TABLE Rp_Studiengang_Steckbriefe_hochschulzentrum
    TO RpStudiengangSteckbriefeHochschulzentrum;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 3) Studiengang
-- ═══════════════════════════════════════════════════════════════════════════════
ALTER TABLE Rp_Studiengang_Steckbriefe_studiengang
    ADD COLUMN Id INT NOT NULL AUTO_INCREMENT FIRST,
    DROP PRIMARY KEY,
    ADD PRIMARY KEY (Id),
    ADD UNIQUE (basis_pk);

-- FK-Spalte: hsb_code (Text) → HochschulbereichId (INT)
ALTER TABLE Rp_Studiengang_Steckbriefe_studiengang
    ADD COLUMN HochschulbereichId INT NOT NULL DEFAULT 0 AFTER abschluss;

UPDATE Rp_Studiengang_Steckbriefe_studiengang sg
    SET sg.HochschulbereichId = (
        SELECT hsb.Id FROM RpStudiengangSteckbriefeHochschulbereich hsb
        WHERE hsb.HsbCode = sg.hsb_code
    );

ALTER TABLE Rp_Studiengang_Steckbriefe_studiengang
    DROP COLUMN hsb_code;

ALTER TABLE Rp_Studiengang_Steckbriefe_studiengang
    CHANGE COLUMN basis_pk BasisPk VARCHAR(30) NOT NULL,
    CHANGE COLUMN display_name Anzeigename VARCHAR(200) NOT NULL,
    CHANGE COLUMN abschluss Abschluss VARCHAR(20) NOT NULL DEFAULT 'Bachelor',
    CHANGE COLUMN regelstudienzeit Regelstudienzeit INT NULL,
    CHANGE COLUMN creditpoints CreditPoints INT NULL,
    CHANGE COLUMN aktiv IstAktiv BOOLEAN NOT NULL DEFAULT TRUE,
    CHANGE COLUMN gueltig_von GueltigVon DATE NULL,
    CHANGE COLUMN gueltig_bis GueltigBis DATE NULL;

ALTER TABLE Rp_Studiengang_Steckbriefe_studiengang
    ADD CONSTRAINT FK_RpSgSteckbriefeStudiengang_Hochschulbereich
        FOREIGN KEY (HochschulbereichId) REFERENCES RpStudiengangSteckbriefeHochschulbereich(Id);

RENAME TABLE Rp_Studiengang_Steckbriefe_studiengang
    TO RpStudiengangSteckbriefeStudiengang;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 4) ProduktKuerzelAlias
-- ═══════════════════════════════════════════════════════════════════════════════
ALTER TABLE Rp_Studiengang_Steckbriefe_produktkuerzel_alias
    ADD COLUMN Id INT NOT NULL AUTO_INCREMENT FIRST,
    DROP PRIMARY KEY,
    ADD PRIMARY KEY (Id),
    ADD UNIQUE (alias_pk);

-- FK-Spalte: basis_pk (Text) → StudiengangId (INT)
ALTER TABLE Rp_Studiengang_Steckbriefe_produktkuerzel_alias
    ADD COLUMN StudiengangId INT NOT NULL DEFAULT 0 AFTER alias_pk;

UPDATE Rp_Studiengang_Steckbriefe_produktkuerzel_alias a
    SET a.StudiengangId = (
        SELECT sg.Id FROM RpStudiengangSteckbriefeStudiengang sg
        WHERE sg.BasisPk = a.basis_pk
    );

ALTER TABLE Rp_Studiengang_Steckbriefe_produktkuerzel_alias
    DROP COLUMN basis_pk;

ALTER TABLE Rp_Studiengang_Steckbriefe_produktkuerzel_alias
    CHANGE COLUMN alias_pk AliasPk VARCHAR(30) NOT NULL,
    CHANGE COLUMN display_name_override AnzeigenameUeberschreibung VARCHAR(200) NULL,
    CHANGE COLUMN aktiv IstAktiv BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE Rp_Studiengang_Steckbriefe_produktkuerzel_alias
    ADD CONSTRAINT FK_RpSgSteckbriefePkAlias_Studiengang
        FOREIGN KEY (StudiengangId) REFERENCES RpStudiengangSteckbriefeStudiengang(Id);

RENAME TABLE Rp_Studiengang_Steckbriefe_produktkuerzel_alias
    TO RpStudiengangSteckbriefeProduktKuerzelAlias;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 5) AnrechnungRegel
-- ═══════════════════════════════════════════════════════════════════════════════
ALTER TABLE Rp_Studiengang_Steckbriefe_anrechnung_regel
    CHANGE COLUMN regel_id Id INT NOT NULL AUTO_INCREMENT,
    CHANGE COLUMN regeltyp Regeltyp VARCHAR(30) NOT NULL,
    CHANGE COLUMN match_operator AbgleichOperator VARCHAR(10) NOT NULL DEFAULT 'EQUALS',
    CHANGE COLUMN match_wert AbgleichWert VARCHAR(400) NOT NULL,
    CHANGE COLUMN kategorie Kategorie VARCHAR(40) NOT NULL,
    CHANGE COLUMN prioritaet Prioritaet INT NOT NULL DEFAULT 100,
    CHANGE COLUMN aktiv IstAktiv BOOLEAN NOT NULL DEFAULT TRUE;

-- Constraints umbenennen (DROP + ADD)
ALTER TABLE Rp_Studiengang_Steckbriefe_anrechnung_regel
    DROP CONSTRAINT CK_Rp_SG_anr_regeltyp,
    DROP CONSTRAINT CK_Rp_SG_anr_operator;

ALTER TABLE Rp_Studiengang_Steckbriefe_anrechnung_regel
    ADD CONSTRAINT CK_RpSgAnrechnungRegel_Regeltyp
        CHECK (Regeltyp IN ('ANRECHNUNGSGRUND','LEISTUNGSART','ANERKANNTTEXT')),
    ADD CONSTRAINT CK_RpSgAnrechnungRegel_Operator
        CHECK (AbgleichOperator IN ('EQUALS','LIKE','IN','NOT_LIKE'));

RENAME TABLE Rp_Studiengang_Steckbriefe_anrechnung_regel
    TO RpStudiengangSteckbriefeAnrechnungRegel;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 6) EndpunktParameter
-- ═══════════════════════════════════════════════════════════════════════════════
ALTER TABLE Rp_Studiengang_Steckbriefe_endpoint_parameter
    ADD COLUMN Id INT NOT NULL AUTO_INCREMENT FIRST,
    DROP PRIMARY KEY,
    ADD PRIMARY KEY (Id);

ALTER TABLE Rp_Studiengang_Steckbriefe_endpoint_parameter
    CHANGE COLUMN endpoint_code EndpunktCode VARCHAR(50) NOT NULL,
    CHANGE COLUMN param_name ParamName VARCHAR(50) NOT NULL,
    CHANGE COLUMN param_wert ParamWert VARCHAR(200) NOT NULL,
    CHANGE COLUMN beschreibung Beschreibung VARCHAR(400) NULL,
    CHANGE COLUMN aktiv IstAktiv BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE Rp_Studiengang_Steckbriefe_endpoint_parameter
    ADD UNIQUE (EndpunktCode, ParamName);

RENAME TABLE Rp_Studiengang_Steckbriefe_endpoint_parameter
    TO RpStudiengangSteckbriefeEndpunktParameter;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 7) Filterliste
-- ═══════════════════════════════════════════════════════════════════════════════
ALTER TABLE Rp_Studiengang_Steckbriefe_filterliste
    CHANGE COLUMN filter_id Id INT NOT NULL AUTO_INCREMENT,
    CHANGE COLUMN bereich Bereich VARCHAR(40) NOT NULL,
    CHANGE COLUMN wert Wert VARCHAR(400) NOT NULL,
    CHANGE COLUMN typ Typ VARCHAR(10) NOT NULL DEFAULT 'EXCLUDE',
    CHANGE COLUMN beschreibung Beschreibung VARCHAR(200) NULL,
    CHANGE COLUMN aktiv IstAktiv BOOLEAN NOT NULL DEFAULT TRUE;

-- Index und Constraint umbenennen
ALTER TABLE Rp_Studiengang_Steckbriefe_filterliste
    DROP INDEX IX_Rp_SG_filterliste_bereich,
    DROP CONSTRAINT CK_Rp_SG_filter_typ;

ALTER TABLE Rp_Studiengang_Steckbriefe_filterliste
    ADD CONSTRAINT CK_RpSgFilterliste_Typ CHECK (Typ IN ('INCLUDE','EXCLUDE')),
    ADD INDEX IX_RpSgFilterliste_Bereich (Bereich, IstAktiv);

RENAME TABLE Rp_Studiengang_Steckbriefe_filterliste
    TO RpStudiengangSteckbriefeFilterliste;

-- ═══════════════════════════════════════════════════════════════════════════════
SELECT 'Migration abgeschlossen – alle Tabellen konventionskonform' AS Status;
