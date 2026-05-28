-- ═══════════════════════════════════════════════════════════════════════════════
-- Studiengang-Steckbriefe: Konfigurations-Datenmodell
-- Datenbank: HochschulorgaApps (MariaDB)
-- Server: mariadb.bcw-intern.local:3306
-- Erstellt: 2026-05-20
-- Aktualisiert: 2026-05-27 (Konventionen: PascalCase, Deutsch, Id-PKs)
-- ═══════════════════════════════════════════════════════════════════════════════
-- Hinweis: Die App liest weiterhin Nutzdaten aus dem SQL Server DWH.
--          Nur die Konfigurations-Tabellen liegen in MariaDB.
-- ═══════════════════════════════════════════════════════════════════════════════

CREATE DATABASE IF NOT EXISTS HochschulorgaApps
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE HochschulorgaApps;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 1) RpStudiengangSteckbriefeHochschulbereich
--    Hochschulbereich-Stammdaten inkl. UI-Metadaten
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS RpStudiengangSteckbriefeHochschulbereich (
    Id              INT             NOT NULL AUTO_INCREMENT,
    HsbCode         VARCHAR(20)     NOT NULL,
    Name            VARCHAR(120)    NOT NULL,
    Icon            VARCHAR(10)     NOT NULL DEFAULT '📚',
    FarbeHex        CHAR(7)         NOT NULL DEFAULT '#607D8B',
    Sortierung      INT             NOT NULL DEFAULT 99,
    IstAktiv        BOOLEAN         NOT NULL DEFAULT TRUE,
    PRIMARY KEY (Id),
    UNIQUE (HsbCode)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 2) RpStudiengangSteckbriefeHochschulzentrum
--    HSZ-Stammdaten mit globalem Ausschluss-Flag und Sortierung
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS RpStudiengangSteckbriefeHochschulzentrum (
    Id              INT             NOT NULL AUTO_INCREMENT,
    Name            VARCHAR(120)    NOT NULL,
    IstAusgeschlossen BOOLEAN       NOT NULL DEFAULT FALSE,
    Sortierung      INT             NOT NULL DEFAULT 100,
    IstAktiv        BOOLEAN         NOT NULL DEFAULT TRUE,
    PRIMARY KEY (Id),
    UNIQUE (Name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 3) RpStudiengangSteckbriefeStudiengang
--    Kanonischer Studiengang (BasisPk als natuerlicher Schluessel)
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS RpStudiengangSteckbriefeStudiengang (
    Id              INT             NOT NULL AUTO_INCREMENT,
    BasisPk         VARCHAR(30)     NOT NULL,
    Anzeigename     VARCHAR(200)    NOT NULL,
    Abschluss       VARCHAR(20)     NOT NULL DEFAULT 'Bachelor',
    HochschulbereichId INT          NOT NULL,
    Regelstudienzeit INT            NULL,
    CreditPoints    INT             NULL,
    IstAktiv        BOOLEAN         NOT NULL DEFAULT TRUE,
    GueltigVon      DATE            NULL,
    GueltigBis      DATE            NULL,
    PRIMARY KEY (Id),
    UNIQUE (BasisPk),
    CONSTRAINT FK_RpSgSteckbriefeStudiengang_Hochschulbereich
        FOREIGN KEY (HochschulbereichId) REFERENCES RpStudiengangSteckbriefeHochschulbereich(Id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 4) RpStudiengangSteckbriefeProduktKuerzelAlias
--    Varianten-Produktkuerzel → Basis-PK Mapping
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS RpStudiengangSteckbriefeProduktKuerzelAlias (
    Id              INT             NOT NULL AUTO_INCREMENT,
    AliasPk         VARCHAR(30)     NOT NULL,
    StudiengangId   INT             NOT NULL,
    AnzeigenameUeberschreibung VARCHAR(200) NULL,
    IstAktiv        BOOLEAN         NOT NULL DEFAULT TRUE,
    PRIMARY KEY (Id),
    UNIQUE (AliasPk),
    CONSTRAINT FK_RpSgSteckbriefePkAlias_Studiengang
        FOREIGN KEY (StudiengangId) REFERENCES RpStudiengangSteckbriefeStudiengang(Id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 5) RpStudiengangSteckbriefeAnrechnungRegel
--    Klassifikationsregeln fuer Anrechnung (Pattern → Kategorie)
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS RpStudiengangSteckbriefeAnrechnungRegel (
    Id              INT             NOT NULL AUTO_INCREMENT,
    Regeltyp        VARCHAR(30)     NOT NULL,
    AbgleichOperator VARCHAR(10)    NOT NULL DEFAULT 'EQUALS',
    AbgleichWert    VARCHAR(400)    NOT NULL,
    Kategorie       VARCHAR(40)     NOT NULL,
    Prioritaet      INT             NOT NULL DEFAULT 100,
    IstAktiv        BOOLEAN         NOT NULL DEFAULT TRUE,
    PRIMARY KEY (Id),
    CONSTRAINT CK_RpSgAnrechnungRegel_Regeltyp
        CHECK (Regeltyp IN ('ANRECHNUNGSGRUND','LEISTUNGSART','ANERKANNTTEXT')),
    CONSTRAINT CK_RpSgAnrechnungRegel_Operator
        CHECK (AbgleichOperator IN ('EQUALS','LIKE','IN','NOT_LIKE'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 6) RpStudiengangSteckbriefeEndpunktParameter
--    Zeitfenster, Rolling-Windows und Schwellwerte je Endpunkt
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS RpStudiengangSteckbriefeEndpunktParameter (
    Id              INT             NOT NULL AUTO_INCREMENT,
    EndpunktCode    VARCHAR(50)     NOT NULL,
    ParamName       VARCHAR(50)     NOT NULL,
    ParamWert       VARCHAR(200)    NOT NULL,
    Beschreibung    VARCHAR(400)    NULL,
    IstAktiv        BOOLEAN         NOT NULL DEFAULT TRUE,
    PRIMARY KEY (Id),
    UNIQUE (EndpunktCode, ParamName)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ═══════════════════════════════════════════════════════════════════════════════
-- 7) RpStudiengangSteckbriefeFilterliste
--    Einfache Include/Exclude-Wertlisten fuer verschiedene Kontexte
-- ═══════════════════════════════════════════════════════════════════════════════
CREATE TABLE IF NOT EXISTS RpStudiengangSteckbriefeFilterliste (
    Id              INT             NOT NULL AUTO_INCREMENT,
    Bereich         VARCHAR(40)     NOT NULL,
    Wert            VARCHAR(400)    NOT NULL,
    Typ             VARCHAR(10)     NOT NULL DEFAULT 'EXCLUDE',
    Beschreibung    VARCHAR(200)    NULL,
    IstAktiv        BOOLEAN         NOT NULL DEFAULT TRUE,
    PRIMARY KEY (Id),
    CONSTRAINT CK_RpSgFilterliste_Typ CHECK (Typ IN ('INCLUDE','EXCLUDE')),
    INDEX IX_RpSgFilterliste_Bereich (Bereich, IstAktiv)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'Alle 7 Konfigurations-Tabellen erstellt' AS Status;
