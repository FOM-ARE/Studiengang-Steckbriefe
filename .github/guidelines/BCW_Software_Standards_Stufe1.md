# BCW Software-Entwicklungsstandards

**Version:** 1.0
**Stand:** März 2026

---

## Einleitung

Dieses Dokument definiert Standards für die Software-Entwicklung in der BCW-Gruppe. Die Standards gelten für alle Software-Projekte, unabhängig davon, ob sie in der IT-Abteilung oder durch Citizen Developer in Fachbateilungen erstellt werden.

### Zielsetzung

- **Qualitätssicherung:** Gewährleistung einer Mindestqualität aller entwickelten Software
- **Interoperabilität:** Sicherstellung der Zusammenarbeit verschiedener Systeme
- **Wartbarkeit:** Langfristige Betreubarkeit durch standardisierte Technologien
- **Security & Compliance:** Einheitliche Sicherheitsstandards und DSGVO-Konformität
- **Effizienz:** Wiederverwendung von bewährten Technologien und Patterns

### Geltungsbereich

Die beschriebenen Standards gelten für alle code-basierten Softwareprojekte – unabhängig davon, wer die Software erstellt. Für Projekte auf zugelassenen Low-Code-Plattformen (Power Apps, Power Automate) gelten die technisch anwendbaren Anforderungen gemäß eigener Vorgaben (hier nicht beschrieben). Projekte, bei denen KI-Werkzeuge zur Code-Generierung eingesetzt werden, fallen uneingeschränkt unter die hier beschriebenen Standards.

## Stufe 1: Grundanforderungen (Verpflichtend)

Diese Standards sind in diesem Geltungsbereich verpflichtend und müssen vor dem ersten Deployment in die Produktivumgebung erfüllt sein. Sie definieren die Mindestbasis in den Bereichen Infrastruktur, Sicherheit, Qualität und Prozesse.

### 1.1 Plattform & Infrastruktur

#### Azure DevOps Plattform
- ✅ **Azure DevOps Organisation BCW-Gruppe** als zentrale Developer-Plattform (Source Control, CI/CD)
- ✅ **Azure Repos / Git** als Versionskontrollsystem
- ✅ **Alle Code-Änderungen müssen versioniert sein** – keine lokalen Entwicklungen ohne Git
- ✅ **Azure Pipelines** als Standard für CI/CD – Nutzung der bereitgestellten BCW-Pipeline-Templates als Ausgangsbasis verpflichtend

**Rationale:** Azure DevOps ist die verbindliche Developer-Plattform der BCW-Gruppe. Die Nutzung der zentralen Organisation stellt Nachvollziehbarkeit, Backup, Zusammenarbeit und konsistente CI/CD-Gates sicher. Pipeline-Templates reduzieren den Aufwand für die Erst-Einrichtung auf ein Minimum.

#### Laufzeitinfrastruktur
- ✅ **Docker** für Containerisierung
- ✅ **Docker-Image-Mindestanforderungen:**
  - Container dürfen nicht als `root` laufen – ein dedizierter Non-root-User muss im Dockerfile angelegt und gesetzt werden
  - Basis-Images müssen aus dem BCW-approbierten Katalog stammen oder auf offiziellen `slim`- bzw. `alpine`-Varianten des Herstellers basieren
  - Keine Secrets dürfen im Image-Layer eingebettet sein (weder als `ENV` noch per `COPY` von Secret-Dateien)
- ✅ **Linux** als Ziel-Betriebssystem
- ✅ **Mirantis Docker Swarm** für Produktiv-Deployments
- ✅ **Traefik** als Reverse Proxy und Routing Layer
- ✅ **Container-basiertes Deployment** – kein direktes Server-Deployment
- ✅ **Container-Registry** - Speicherung und Bezug von Container-Images für Produktiv-Workloads erfolgen ausschließlich über die Mirantis Secure Registry (MSR) als Bestandteil der Mirantis Docker Swarm Plattform.
- ✅ **SonarQube cloud** Analyse vor Produktiv-Deployments

**Rationale:** Docker Swarm als etabliertes Orchestrierungssystem; Die Image-Mindestanforderungen verhindern typische Sicherheitslücken, die erfahrungsunabhängig auftreten (Root-Container, Secret-Leaks, aufgeblähte Images); Traefik als etablierter Proxy; Linux als standardisiertes, ressourceneffizientes Zielsystem. 

#### Secrets Management
- ✅ **Azure Key Vault** für Secrets und sichere Verwaltung von Credentials

**Rationale:** Zentrales, sicheres Secrets-Management als Plattform-Standard.

#### Logging & Basis-Monitoring
- ✅ **Strukturiertes Logging** verpflichtend: Logs müssen auf `stdout`/`stderr` ausgegeben werden (Container-Standard). Jeder Log-Eintrag muss ein strukturiertes JSON-Objekt mit folgenden Pflichtfeldern sein:
  - `timestamp` – ISO 8601 (z. B. `2026-03-02T14:32:00.000Z`)
  - `level` – eines von: `debug`, `info`, `warn`, `error`
  - `message` – menschenlesbare Beschreibung des Ereignisses
  - Mindest-Ereignisse: alle Fehler (`error`), alle Warnungen (`warn`), Start und Stop der Anwendung
- ✅ **Basis-Monitoring** für Verfügbarkeit verpflichtend – jede Anwendung muss einen Health-Endpoint unter `/health` oder `/healthz` exponieren, der:
  - **HTTP 200** zurückgibt, wenn die Anwendung betriebsbereit ist
  - **HTTP 503** zurückgibt, wenn die Anwendung nicht betriebsbereit ist (z. B. Datenbankverbindung fehlt, Initialisierung noch nicht abgeschlossen)
  - Das Response-Body-Format ist freigestellt; ein einfaches `{ "status": "ok" }` ist ausreichend

**Rationale:** Logging auf `stdout`/`stderr` ist der Container-Standard und vermeidet Probleme mit Pfaden, Datei-Rotation und vollen Volumes. Die Anwendung ist verantwortlich dafür, Logs strukturiert bereitzustellen und ihre Verfügbarkeit über einen standardisierten Health-Endpoint signalisierbar zu machen. Die Infrastruktur für zentralisiertes Logging, Metriken und Alerting ist Plattformaufgabe und wird nicht von jedem Entwicklerteam individuell aufgesetzt.

### 1.2 Sicherheit

- ✅ **Keine Hard-coded Credentials** – Passwords, API-Keys und Secrets ausschließlich über Azure Key Vault. Im lokalen Entwicklungsumfeld sind Secrets alternativ über plattformspezifische Mechanismen wie .NET User Secrets, systemweite Umgebungsvariablen oder eine lokale `.env`-Datei erlaubt, sofern diese nicht ins Repository eingecheckt wird (`.gitignore`-Pflicht). CI/CD- und Produktivumgebungen nutzen ausschließlich Azure Key Vault.
- ✅ **HTTPS/TLS>=1.3** für alle web-basierten Services und APIs verpflichtend
- ✅ **Input-Validierung** und **Output-Encoding** gegen Injection-Attacks – konkret bedeutet das:
  - **Datenbankzugriff:** Ausschließlich Prepared Statements / parametrisierte Queries – kein dynamisches SQL-String-Building (gilt für alle Datenbanktechnologien; bei Entity Framework Core ist dies standardmäßig erfüllt, sofern kein Raw-SQL ohne Parameter verwendet wird)
  - **User-Input validieren:** Eingaben auf erwartetes Format, Länge und Typ prüfen, bevor sie verarbeitet oder gespeichert werden – serverseitig, nicht nur im Frontend.
  - **HTML-Output encoding:** Kein direktes Einfügen von User-Daten in HTML (`innerHTML`, `Html.Raw()`) – React und Angular schützen automatisch, solange diese Mechanismen nicht umgangen werden
  - **API-Input:** Request Bodies und Query-Parameter an API-Endpunkten validieren – nicht blind vertrauen, auch bei internen APIs
  - **Hinweis für Teams ohne Security-Erfahrung:** SonarQube erkennt typische Injection-Schwachstellen automatisch; gefundene Issues mit Severity `High` oder `Blocker` sind ohnehin gemäß Abschnitt 1.3 zu beheben
- ✅ **Active Directory / EntraID** als zentraler Identity Provider für Benutzeridentitäten – Identitäten werden im on-premises Active Directory verwaltet und nach EntraID synchronisiert; Es wird kein lokales User-Management implementiert; Applikationen binden sich gegen EntraID an. Jede Abweichung von dieser Anforderung ist zwingend als ADR zu dokumentieren, inklusive Begründung und Kompensationsmaßnahmen.
- ✅ **OAuth 2.0 / OpenID Connect** als Standard-Protokolle für Authentifizierung und Autorisierung
- ✅ **Keine sensitiven Daten in Logs** (Passwords, PII ohne Maskierung)

**Rationale:** Schutz vor den OWASP Top 10 Sicherheitsrisiken als universelle Mindestanforderung. Active Directory ist das primäre System of Record für Benutzeridentitäten in der BCW-Gruppe; EntraID ist die bevorzugte Anbindeschicht für Applikationen. Durch die Vorgabe eines zentralen Identity Providers wird das Lifecycle-Management (Onboarding, Offboarding, Rollenänderungen) an einer einzigen Stelle gesteuert. Die Pflicht zur Authentifizierung aller Endpunkte unterbindet versehentlich öffentlich erreichbare APIs – ein häufiger Angriffsvektor, der durch klare Ausnahmeregelungen gleichzeitig praxistauglich bleibt.

### 1.3 Code-Qualität & Dependency Management

- ✅ **SonarQube Issues**: Issues mit severity `Blocker` und `High` müssen behoben sein. Suppressions sind nur unter folgenden Bedingungen zulässig:
  - **Suppression via SonarQube-UI** (Won't Fix / False Positive): Eine schriftliche Begründung ist als Kommentar am Issue in SonarQube zu hinterlegen. Suppressions von `Blocker`-Issues erfordern zusätzlich die Zustimmung eines zweiten Reviewers.
  - **Suppression via `// NOSONAR` im Code**: Jedes `// NOSONAR`-Kommentar muss im zugehörigen Pull Request mit einer Begründung kommentiert und vom Reviewer explizit akzeptiert werden. Unbegründete `// NOSONAR`-Kommentare sind im Code-Review abzulehnen.
- ✅ **Strukturelle Trennung von Fachlogik und Infrastruktur:** Code, der fachliche Regeln implementiert (Berechnungen, Validierung, Prozesssteuerung), darf keine direkten Aufrufe auf Datenbankzugriffe (z. B. EF Core DbContext, SQL-Queries), Datei-System, HTTP-Clients oder externe APIs enthalten. Der Zugriff auf Infrastruktur erfolgt ausschließlich über Interfaces.
  - Code-Reviews prüfen: Ist die Fachlogik ohne Infrastrukturkomponenten unit-testbar?
  - Gilt nicht für: Skripte, Utility-Code und Konfigurationsklassen
- ✅ **Aussagekräftige Bezeichner**: Variablen-, Funktions- und Klassennamen müssen den Zweck klar ausdrücken; Abkürzungen vermeiden. Die verwendete Sprache (Deutsch oder Englisch) muss innerhalb einer Codebase konsistent sein.
- ✅ **Kein toter Code** in Produktionscode: kein auskommentierter Code, keine unbenutzten Variablen oder Methoden
- ✅ **Konsistente Formatierung**: Ein sprachüblicher Formatter muss angewendet sein (`dotnet format`, Prettier, Black o. Ä.) – kein vorgeschriebener Style, aber einheitliche Formatierung innerhalb der Codebase
- ✅ **Mindestens 1 Code-Review** vor Merge in den Main-Branch. Der Main-Branch ist geschützt. Merges erfolgen ausschließlich per Pull Request mit mindestens 1 erfolgreichem Review (Approval).
- ✅ **Alle Dependencies dokumentiert** (NuGet, npm etc.)
- ✅ **Bekannte Vulnerabilities** in eingesetzten Dependencies müssen behoben werden (toolabhängig: `npm audit`, `dotnet list package --vulnerable`, etc.)

**Rationale:** Automatisierte und manuelle Qualitätssicherung als universelle Mindestbasis; Vermeiden von Code Smells, Vulnerabilities und Supply-Chain-Risiken. Die strukturelle Trennung von Fachlogik und Infrastruktur ist eine bewusst technologieneutrale Mindestanforderung: Sie verhindert enge Kopplung an konkrete Datenbank- oder Infrastrukturimplementierungen, erleichtert das isolierte Testen von Business-Logik ohne Datenbankverbindung und reduziert langfristig den Wartungsaufwand bei Infrastrukturwechseln. Die Anforderungen sind bewusst stack-neutral gehalten und gelten unabhängig von Projektgröße oder eingesetztem Stack. Weitergehende Style-Vorgaben, Branch-Strategien und Review-Prozesse sind in Stufe 2 (Abschnitt 2.7) beschrieben.

### 1.4 Entwicklungspraktiken

#### Deployment & CI/CD
- ✅ **Deployment ausschließlich über Azure Pipelines** – keine manuellen Deployments in Produktiv-Umgebungen
- ✅ **BCW-Standard-Pipeline-Templates** verwenden (enthält Build, Test, SonarQube, Container-Build)
- ✅ **Rollback-Möglichkeit** definiert und im README dokumentiert

#### Dokumentation
- ✅ **Docs-as-Code:** Dokumentation im Markdown-Format in Ordner /docs im Git-Repository.
- ✅ **Architecture Decision Records (ADRs)** für alle relevanten Architekturentscheidungen im Markdown-Format im Ordner docs/decisions. Ein ADR ist in der Regel erforderlich, wenn mindestens eines der folgenden Kriterien zutrifft:
  - Die Entscheidung weicht von einer Empfehlung in Stufe 2 ab
  - Mehrere Systeme oder Teams sind betroffen
  - Die Entscheidung ist schwer oder mit hohem Aufwand rückgängig zu machen
  - **Typische Beispiele:** Wahl des Datenbanktyps, Framework-/Library-Entscheidungen mit signifikantem Architektureinfluss, API-Schnittstellendesign, Authentifizierungskonzept, Abweichungen von BCW-Standards
  - **Keine ADRs erforderlich für:** Bibliotheks-Versionen ohne Architekturrelevanz, Implementierungsdetails, rein interne Refactorings

#### Testing
- ✅ **Unit-Tests** sind verpflichtend für Business-Logik, Validierungsregeln und Fehlerbehandlung. Code-Reviews prüfen, ob die relevanten Pfade abgedeckt sind.

**Rationale:** Die Verantwortung für sinnvolle Testabdeckung liegt beim Entwickler und wird im Code-Review geprüft - eine quantitative Coverage-Kennzahl allein ist kein hinreichendes Qualitätskriterium; weitergehende Test-Strategien sind in Stufe 2 beschrieben.

### 1.5 Betrieb & Ownership

- ✅ **Verantwortliches Team/verantwortliche Person** festgelegt
- ✅ **Kontaktinformationen** im README dokumentiert
- ✅ **Oncall/Support-Prozess** definiert (auch wenn „Best Effort") und im README dokumentiert

**Rationale:** Klare Verantwortlichkeiten; keine „verwaisten" Anwendungen.

---

*Stand: 06. März 2026*