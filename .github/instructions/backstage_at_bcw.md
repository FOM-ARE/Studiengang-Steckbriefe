# 🧭 Backstage Setup & Nutzung – Best Practice Leitfaden

## Inhalt
1 Zielbild
2 Technische Architektur
3 Entity-Modellierung (Katalogstruktur)
4 Repository‑Struktur
5 Naming‑Konventionen
6 Techdocs
7 Governance 
8 YAML-Beispiele

---

## 1️⃣ Zielbild

Backstage dient als **zentrales Developer Portal**, um:

- die **Systemlandschaft transparent** abzubilden und deren Bestandteile zu dokumentieren,
- **Komponenten und Services auffindbar** zu machen,
- **Self-Service** für Teams (z. B. durch Templates) zu ermöglichen.

Backstage fungiert als **Single Source of Truth** für technische Artefakte und Metadaten innerhalb der Systemlandschaft. Den zentralen Punkt hierbei bildet der Backstage Katalog, in welchem alle Bestandteile der Systemlandschaft gepflegt werden.

---

## 2️⃣ Technische Architektur

| Komponente | Zweck | Quelle |
|-------------|--------|--------|
| **Backstage Core** | Zentrales Portal und Katalog | Docker Service |
| **Catalog Plugin** | Verwaltung der Entities (YAML-Dateien) | Azure DevOps Repos |
| **TechDocs Plugin** | Anzeige von Markdown-Dokumentation | Aus Repos generiert |
| **Auth Provider** | Single Sign-On | Microsoft Entra ID (Azure AD) |
| **Search Plugin** | Volltextsuche über Entities | Elasticsearch oder PostgreSQL |

Zukünftig kann die Plattform um zusätzliche Komponenten erweitert werden. 

---

## 3️⃣ Entity‑Modellierung (Katalogstruktur)

### Grundprinzip

Jede Entität im Katalog beschreibt **einen eindeutig identifizierbaren Bestandteil** der Systemlandschaft. Die Modellierung orientiert sich an der logischen Architektur.

Eine ausführliche Beschreibung aller Typen von Entitäten und ihrer Bedeutung findet sich unter: https://backstage.io/docs/features/software-catalog/system-model

Wir verwenden folgende Entitäten-Typen:

Technische Entitäten
- System
- Component
- API
- Resource

Ecosystem Entitäten
- Domain
- User
- Group  

Jede Entität wird mit den zugehörigen Metadaten in einem "catalog-info" YAML file beschrieben und damit in den Backstage Katalog aufgenommen.  

#### 🔹 3.1 Technische Entitäten

Technische Artefakte werden durch technische Entitäten abgebildet. 

#### 🔹 3.1.1 System

Ein System beschreibt einen **logisch zusammenhängenden Verbund von Komponenten und Ressourcen**, der gemeinsam betrieben oder verwaltet wird.

Beispiele:
- `system: studieneinstieg`
- `system: anrechnung`
- `system: elastic-stack`
- `system: azure-devops`

#### 🔹 3.1.2 Component

Components sind **Anwendungseinheiten oder Services**, die innerhalb eines Systems laufen. Wir unterscheiden folgende Typen von Components:

| Component type | Bedeutung |
|------------|------------|
| `service` | Backend service, Worker, Microservice |
| `frontend` | Frontend App |
| `self-contained-system` | Self-Contained System mit integriertem Frontend und Backend |
| `library` | Libraries/Packages |
| `powerapp` | Microsoft Power App |
| `powerflow` | Microsoft Power Automate Flow |
| `desktop-app` | Desktop-Anwendungen (VB6, WinForms, WPF) |
| `infrastructure` | Infrastruktur-Komponenten (Deployment Scripts, IAC Modules...) |

Beispiele:
- `component: digaonlineservice, type service`
- `component: anrechnungsservice, type service`
- `component: kibana, type infrastructure`
- `component: azure-pipelines, type infrastructure`

**Besonderheit bei der Modellierung von Self-Contained Systems:**

Self-Contained Systems (SCS) sind autonome, in sich geschlossene Systeme. Bei der Modellierung in Backstage stellt sich die Frage nach der System-Ebene:

**Empfehlung:**
- **SCS direkt an Domain** (ohne `spec.system`), wenn das SCS völlig eigenständig ist und keinen fachlichen Verbund mit anderen Components bildet
- **SCS mit System-Ebene** nur, wenn mehrere SCS/Components thematisch zusammengehören und gemeinsam einen fachlichen Kontext bilden

**Vermieden werden soll** dauerhaft Systems mit nur einer Component – dies schafft unnötige Hierarchieebenen.

*Die System-Ebene ist in Backstage optional. Die Domain-Zuordnung ist die zentrale fachliche Gruppierung.*

#### 🔹 3.1.3 API

APIs ermöglichen Zugang zu Funktionen von Components oder Ressources und werden von diesen bereitgestellt. Je nach Art werden verschiedene Typen von APIs unterschieden:

| API type | Bedeutung |
|------------|------------|
| `openapi` | HTTP/REST APIs (OpenAPI/Swagger) |
| `asyncapi` | Eventbasierte/Message-basierte APIs (z. B. RabbitMQ Queues) |
| `soap` | SOAP APIs |
| `grpc` | gRPC-Services |

Beispiele:
- `api: digaonlineservice-mqapi, type asyncapi`
- `api: anrechnungsservice-webapi, type openapi`
- `api: kibana-api, type openapi`
- `api: azure-devops-restapi, type openapi`

#### 🔹 3.1.4 Resource

Resources sind **technische Infrastrukturressourcen**, auf die Components zugreifen. Wir unterscheiden folgende Typen von Resources: 

| Resource type | Bedeutung |
|------------|------------|
| `database` | MariaDB, MSSQL, MongoDB... |
| `container-orchestrator` | Docker Swarm |
| `registry` | Harbor, ACR... |
| `vault` | Azure Key Vault |
| `queue` | RabbitMQ Queue, Azure ServiceBus Queue... |
| `observability` | Elasticsearch, Kibana, metricbeat... |
| `devops-service` | Azure Pipelines, Azure Repos... |
| `server` | VM, Bare Metal, Cloud Instance... |

Beispiele:
- `resource: mariadb-onlineanmeldungen, type database`
- `resource: sbq-, type queue`
- `resource: elasticsearch-prod, type observability`
- `resource: azure-devops-01, type server`

### 🔹 3.2 Ecosystem Entitäten

Um unser gesamtes Ecosystem inkl. organisatorischer Elemente wie fachliche Domänen und Teams in Backstage abbilden zu können, nehmen wir auch nicht-technische Entitäten in den Backstage Katalog auf.

#### 🔹 3.2.1 Domain

Domains sind **geschäftliche oder technische Verantwortungsbereiche** – die oberste Hierarchieebene im Katalog. Dies entspricht somit unseren Domänen, welche wir mit diesem Entiäts-Typ abbilden.

- `domain: interessentenakquise-und-betreuung`
- `domain: teilnehmerbetreuung`
- `domain: lehrendenbetreuung-und-pruefungsmanagement`
- `domain: produktmanagement-und-durchfuehrungsorganisation`
- `domain: bcw-plattform`

#### 🔹 3.2.2 User

User bilden die Benutzer Entitäten in Backstage und dienen primär der Identifikation der Benutzer, auch für die Authentifizierung. Im Modell werden die Benutzer als Mitglieder in Group Entitäten dargestellt.

User werden nicht als "catalog-info" YAML files dem Katalog hinzugefügt, sondern über die Entra ID Anbindung von Backstage aus dem Entra ID-Verzeichnis importiert.

**Wichtig:** Da wir User aus EntraID übernehmen, gelten hier nicht die in diesem Dokument beschriebenen Naming-Regeln zu Backstage Entitäten. User werden so übernommen, wie sie in EntraID erfasst sind.

#### 🔹 3.2.3 Group

Groups repräsentieren organisatorische Einheiten, typischerweise Teams. Wir bilden damit im Zusammenspiel mit User Entitäten unsere Teamsstrukturen ab. Innerhalb des Modells setzen wir Groups primär für die Beschreibung der Ownership von Entitäten ab (siehe auch Beziehungen zwischen Entitäten --> Entitäten Ownership).

Groups werden nicht als "catalog-info" YAML files dem Katalog hinzugefügt, sondern über die Entra ID Anbindung von Backstage aus dem Entra ID-Verzeichnis importiert.

Beispiele:
- `group: IT.Se.Domaene.Interessenten`
- `group: IT.Se.Domaene.Teilnehmer`
- `group: devops-platform-orchestration-automation`

Neben der Rolle im Modell können Groups auch im Rechte & Rollen System von Backstage selbst genutzt werden.

**Wichtig:** Da wir Groups aus EntraID übernehmen, gelten hier nicht die in diesem Dokument beschriebenen Naming-Regeln zu Backstage Entitäten. Groups werden so übernommen, wie sie in EntraID erfasst sind.

### 🔹 3.3 Location

Location dient als Einstiegspunkt für weitere YAML-Dateien. Location beschreibt somit nicht eine Entität wie Component, API oder System, sondern eine Sammlung von Entitäten, die an einem bestimmten Ort liegen.

```yaml
apiVersion: backstage.io/v1alpha1
kind: Location
metadata:
  name: domain-produktmanagement-und-durchfuehrungsorganisation-catalog
  description: Backstage Katalog für die Domäne Produktmanagement und Durchführungsorganisation.
spec:
  type: url
  targets:
    - https://dev.azure.com/BCW-Gruppe/...?path=/domain-produktmanagement-und-durchfuehrungsorganisation-software-catalog-info.yaml
    - https://dev.azure.com/BCW-Gruppe/...?path=/Systems/Kurszuordnung/system-kurszuordnung-software-catalog-info.yaml
    - https://dev.azure.com/BCW-Gruppe/...?path=/Systems/MoodleZoomSynchronization/system-moodle-zoom-sync-software-catalog-info.yaml
```

Konkrete Verwendungen von Location werden in den Abschnitten 4.2 und 4.3 aufgeführt.

### 🔹 3.4 Namespaces in Backstage

Backstage organisiert Entities in Namespaces, die eine logische Gruppierung ermöglichen. Standardmäßig nutzen wir den **`default` Namespace** für alle unsere Entitäten.

**Vollständige Referenzierung:**
```yaml
dependsOn:
  - resource:default/mariadb-onlineanmeldungen
  - component:default/anrechnungsservice
```

**Verkürzte Schreibweise:**
Wenn eine Entity im `default` Namespace liegt, kann der Namespace weggelassen werden:
```yaml
dependsOn:
  - resource:mariadb-onlineanmeldungen
  - component:anrechnungsservice
```

Beide Schreibweisen sind äquivalent und referenzieren dieselbe Entity. Wir empfehlen die **verkürzte Schreibweise**, da sie übersichtlicher ist und wir ausschließlich den default Namespace verwenden.

**Wichtig:** Sollten zukünftig weitere Namespaces eingeführt werden (z.B. für externe Systeme oder unterschiedliche Mandanten), muss bei Referenzen über Namespace-Grenzen hinweg die vollständige Schreibweise `kind:namespace/name` verwendet werden.

### 🔹 3.5 Beziehungen zwischen Entitäten

#### 🔹 3.5.1 Abhängigkeit

Die typische Form der Beziehung zwischen Entitäten ist die Abhängigkeit. Abhängigkeiten werden über `dependsOn` bzw. `dependencyOf` definiert:

Components sind in der Regel immer abhängig von Resources. Aber auch Abhängigkeit zwischen Components untereinander oder zwischen Resources sind häufig gegeben und können entsprechend abgebildet werden. Der Fokus liegt hierbei auf Abhängigkeiten zur Laufzeit. Abhängigkeiten bei Build oder Deployment werden in der Regel nicht modelliert.

Wir modellieren diese Beziehung immer von der abhängigen Seite. Wenn meine Component also von einer Resource abhängig ist, beschreibe ich diese Abhängikeit über `dependsOn` in meiner Component. Die Darstellung der Abhängigkeit von der Resource aus betrachtet, stellt Backstage automatisch dar. `dependencyOf` wird damit in der Regel nicht explizit beschrieben.

```yaml
spec:
  dependsOn:
    - resource:default/mariadb-onlineanmeldungen
    - component:default/elowebservice
```

**Wichtig:** Werte müssen Strings im Format `kind:namespace/name` sein (siehe Abschnitt 3.4 für Details zu Namespaces).

#### 🔹 3.5.2 API Provisionierung/Konsumierung

Eine besondere Form der Beziehung gilt für APIs. Dies werden typischerweise von einer Component implementiert und durch diese bereitgestellt (provisioniert). Diese Bereitstellung wird in der Component über `providesApis` definiert.

Auch das Konsumieren einer API durch eine Entität kann beschrieben werden. Dies geschieht über `consumesApis`.

```yaml
spec:
  providesApis:
    - customer-api
  consumesApis:
    - contract-api
``` 

#### 🔹 3.5.3 Entitäten Ownership

Eine weitere spezielle Form der Beziehung ist die Ownership. Jede Entität benötigt einen `spec.owner`. 

Ownership liegt in der Regel immer bei einem Team. Teams werden als Group Entitäten im Katalog gepflegt.

```yaml
spec:
  owner: IT.Se.Domaene.Teilnehmer
```

#### 🔹 3.5.4 Entitäten Zugehörigkeit

Die Zugehörigkeit einer Entität (in der Regel Component oder System) zu einer übergeordneten Entität (in der Regel System oder Domain) wird über `spec.system` oder `spec.domain` dokumentiert. 

```yaml
spec:
  system: studieneinstieg
```

```yaml
spec:
  domain: teilnehmerbetreuung
```
Auch hier modellieren wir diese Beziehung immer von der abhängigen Seite. Wenn also zum Beispiel meine Component Teil eines Systems ist, beschreibe ich diese Zugehörigkeit über `spec.system` in meiner Component. Die Darstellung der Zugehörigkeit vom System aus betrachtet, stellt Backstage automatisch dar.

### 🔹 3.6 Lifecycle‑Standard

`spec.lifecycle` beschreibt den **Reifegrad** einer Entität (nicht die Umgebung). Wir verwenden folgende Standardwerte für die verschiedenen Phasen im Lifecycle einer Entität.

| Lifecycle | Bedeutung |
|------------|------------|
| `experimental` | Prototyp, Proof of Concept |
| `development` | Pre-Release Entwicklung / Test |
| `production` | Produktivbetrieb |
| `maintenance` | Keine aktive Weiterentwicklung mehr, Nur noch Fehlerbehebung |
| `deprecated` | Abgekündigt, Ablösung geplant |
| `retired` | Historisch, Abgeschaltet |

```yaml
spec:
  lifecycle: production
```

Umgebungen (prod, staging, dev) werden stattdessen über `metadata.tags` kenntlich gemacht Siehe hierzu Abschnitt 3.7.1.

### 🔹 3.7 Custom Metadata

Individuelle, optionale Zusatzinformationen können über Tags oder Annotations hinterlegt werden.

#### 🔹 3.7.1 Tags

Tags können als zusätzliches Werkzeug für Ordnung und Such-Optimierung im Software Katalog verwendet werden. Es können zusätzliche Informationen zu Entitäten hinterlegt werden, zum Beispiel:

- Welche Technologie?
- Welche Betriebsart?
- ...

```yaml
metadata:
  tags:
    - dotnet
    - on-prem
```

**Wichtig:** Tags helfen nur, wenn sie sparsam verwendet werden. 5 bis 10 Tags pro Entität sind in Ordnung. Werden regelmäßig mehr als 10 Tags verwendet, sollte die Modellierung hinterfragt werden.

#### 🔹 3.7.2 Annotations

Annotations erlauben individuelle Erweiterungen, z.B. Umgebungs‑ oder Dashboard‑Links. Diese können bei Bedarf verwendet werden. Einige Beispiele für regelmäßig verwendete Annotations (teilweise mit Bezug zu spezifischen Plugins) finden sich unter https://backstage.io/docs/features/software-catalog/well-known-annotations

```yaml
metadata:
  annotations:
    dev.azure.com/project-slug: "DevOps"
    monitoring/dashboard-url: "https://grafana.local/elastic"
```

**Wichtig:** Der Pfad für Techdocs wird ebenfalls als Annotation hinterlegt. Dieser ist nicht optional. Siehe hierzu Abschnitt `Techdocs`. 

---

## 4️⃣ Repository‑Struktur

Die für die Aufnahme von Entitäten in den Backstage Katalog erforderlichen "catalog-info" YAML files werden als Teil des Codes in unseren Code Repositories gespeichert. 

### 🔹 4.1 Component-Repository

Für Components innerhalb einer Domäne werden die zugehörigen "catalog-info" YAML files als Teil des Codes im root des Repository der Component gespeichert. Im Component-Repository liegen:

- Die **Component** selbst
- Jede **Resource**, die **ausschließlich von dieser Component** genutzt wird (z.B. eine dedizierte Datenbank)

Resources, die von **mehreren Components gemeinsam** genutzt werden, gehören ins Domain-Repository (siehe Abschnitt 4.2).

**APIs gehören nicht ins Component-Repository**, sondern immer ins Domain-Repository (siehe Abschnitt 4.2). Die technische API-Spec (z.B. OpenAPI-Datei) verbleibt jedoch im Component-Repository und wird vom API-Entitäts-YAML per URL referenziert.

```
/AnrechnungsService
  component-anrechnungsservice-software-catalog-info.yaml
  resource-mariadb-anrechnungen-software-catalog-info.yaml
  openapi.yaml                         # API-Spec, wird per URL referenziert
  ...
  Api.Contracts/
  Application/
  DataAccess/
  ...
```

### 🔹 4.2 Domain-Repository

Für Entitäten in einem Domänen-Kontext jenseits von Components nutzen wir ein dediziertes Domain-Repository je Domäne. Dort liegt ein zentrales "catalog-info" YAML file `software-catalog-info.yaml`, ein "catalog-info" YAML file `domain-domänenName-software-catalog-info.yaml` für die Domäne selbst sowie Unterordner je Entitätstyp und darin Unterordner je Entität mit dem YAML file der jeweiligen Entität. Aus `software-catalog-info.yaml` wird auf die YAML files der einzelnen Entitäten verwiesen (über `location`).

Ins Domain-Repository gehören:

- **Systems** der Domäne
- **Alle APIs**, unabhängig davon, durch welche Component sie implementiert werden – die API ist ein fachlicher Vertrag der Domäne und bleibt damit stabil, auch wenn die implementierende Component ausgetauscht wird
- **Resources, die von mehreren Components gemeinsam genutzt werden** (z.B. eine geteilte Datenbank oder eine domänenweit genutzte Queue)

**Wichtig:** Component-exklusive Resources (nur von einer einzigen Component genutzt) gehören ins Component-Repository, nicht hierher. Wird eine solche Resource später auch von weiteren Components genutzt, ist das YAML ins Domain-Repository zu verschieben und die Location-Datei entsprechend zu aktualisieren.

**API-Spec per URL referenzieren:** Die eigentliche API-Spec (OpenAPI, AsyncAPI...) liegt und ändert sich im Component-Repository der implementierenden Component. Das API-Entitäts-YAML im Domain-Repository referenziert sie daher per URL, statt die Spec inline zu wiederholen. So muss bei Änderungen an der Spec (z.B. neuer Endpoint) nur das Component-Repository angepasst werden – das Domain-Repository bleibt unberührt.

```yaml
spec:
  type: openapi
  definition:
    $text: https://dev.azure.com/BCW-Gruppe/StudiengangSteckbriefe/openapi.yaml
```

Das Domain-Repository muss nur bei strukturellen Änderungen an der API-Entität selbst angefasst werden (z.B. Namensänderung, Lifecycle-Wechsel, neuer Owner).

```
/domain-teilnehmerbetreuung/
  software-catalog-info.yaml
  domain-teilnehmerbetreuung-software-catalog-info.yaml
  systems/
    system-studieneinstieg/
      system-studieneinstieg-software-catalog-info.yaml
    ...
  apis/
    api-anrechnungsservice-webapi/
      api-anrechnungsservice-webapi-software-catalog-info.yaml   # Spec per URL referenziert
    ...
  resources/
    resource-mariadb-shared/          # nur geteilte Resources
      resource-mariadb-shared-software-catalog-info.yaml
    ...
```

### 🔹 4.3 Zentrales Repository für Plattform Infrastruktur

Zentrale Elemente unserer Landschaft bilden Infrastruktur-Systeme, welche Plattform-Services bereitstellen. Für diese Systeme und ihre Teile (Components, APIs, Resources...) gibt es regelmäßig keine Repositories. Um diese Entitäten im Backstage Katalog aufnehmen zu können, speichern wir die erforderlichen "catalog-info" YAML files in einem zentralen Repository für die Plattform Infrastruktur. Aus dem zentralen "catalog-info" YAML file `software-catalog-info.yaml` wird auf die YAML files der einzelnen Entitäten verwiesen (über `location`).

```
/platform-resources/
  software-catalog-info.yaml
  systems/
    system-azure-devops/
      system-azure-devops-software-catalog-info.yaml
    ...
  components/
    component-elasticsearch/
      component-elasticsearch-software-catalog-info.yaml
    component-kibana/
      component-kibana-software-catalog-info.yaml
    ...
  resources/
    resource-azure-devops-01/
      resource-azure-devops-01-software-catalog-info.yaml
    resource-mir-dev-mgmt-01/
      resource-mir-dev-mgmt-01-software-catalog-info.yaml 
    ...
  apis/
    ...
```

---

## 5️⃣ Naming‑Konventionen

Die Einhaltung klarer Naming-Regeln erleichtert Suche und Automation.

Alle Namen werden in **Kleinbuchstaben** geschrieben, ohne Sonderzeichen oder Leerzeichen. Bindestriche können als Trennzeichen verwendet werden.  

### 🔹 5.1 Entitäten Namen

Dem Entitäten-Namen wird jeweils der Entitäten-Typ vorangestellt.

`system-studieneinstieg`
`component-anrechnungsservice`
`api-digaonlineservice-mqapi`
`resource-mariadb-onlineanmeldungen`
`domain-teilnehmerbetreuung`

### 🔹 5.2 catalog-info.yaml

Das "catalog-info" YAML file einer Entität wird nach folgendem Schema benannt:

studiengangsteckbriefe-software-catalog-info.yaml

Eine Ausnahme von diesem Schema bilden zentrale YAML files, welche in größeren Strukturen lediglich zum Verweis auf spezifische YAML files dienen (typisch bei Domain und Plattform Infrastruktur Repositories). Diese werden vereinfacht mit **software-catalog-info.yaml** bezeichnet.  

---

## 6️⃣  Dokumentation mit Techdocs

Für die Dokumentation unserer Entitäten nach einem docs-like-code Ansatz nutzen wir das Backstage Plugin Techdocs. Dokumentationen werden dabei in Markdown im jeweiligen Repository gepflegt, folgen einer einheitlichen Struktur und werden automatisiert in Backstage veröffentlicht.

### 🔹 6.1 Abgrenzung: Dokumentationen vs. Software Katalog

Dokumentationen stehen in diesem Zusammenhang für alle Dokumente und vergleichbare Artefakte, welche die Architektur und Struktur einer Entität erklären, das Onboarding von Entwicklern beschleunigen sowie Betrieb und Ownership transparent machen.
Auch wenn der Backstage Software Katalog ebenfalls eine übergreifende Dokumentations-Funktion erfüllt, ist dieser von der spezifischen Dokumentation einer Entität abzugrenzen. 

| Backstage Katalog      | Dokumentationen         |
| ---------------------- | ----------------------- |
| Struktur & Beziehungen | Inhalte & Erläuterungen |
| Ownership              | Entscheidungsgrundlagen |
| Abhängigkeiten         | Architekturdetails      |
| Metadaten              | How-tos & Konzepte      |

Kurz gesagt: Der Software Katalog sagt, was es gibt – Dokumentationen erklären, wie und warum.

### 🔹 6.2 Techdocs-Stack

Für die automatisierte Verarbeitung der Dokumentationen nutzen wir einen einheitlichen Stack:

- Format: Markdown
- Diagramme: Mermaid
- Theme: mkdocs-material
- Generator & Build: Mit MkDocs automatisiert (in Techdocs und CI integriert) 

### 🔹 6.3 Verzeichnisstruktur für Dokumentationen von Components

Alle Artefakte der Dokumentation einer Component sind im Repository der Component im Ordner `docs` gespeichert. Dort findet sich immer eine Datei `index.md`, welche eine kurze Beschreibung der Entität enthält sowie eine Datei `mkdocs.yml` für die MkDocs Konfiguration. Weiterhin findet sich dort immer mindestens eine Datei mit der Architekturdokumentation. Für komplexere Entitäten kann die Architekturdokumentation auch auf mehrere Dateien aufgeteilt werden. Für dokumentierte Architekturentscheidungen zu der Entität gibt es immer einen Unterornder `decisions`. Liegen keine Entscheidungsdokumente vor, ist der Ordner ggf. leer.  

```
/docs/
  index.md
  mkdocs.yml
  architecture.md
  decisions/
    adr-001.md
    adr-002.md
    ...
  ...
```

Optional können nach individuellem Bedarf weitere Artefakte hinzugefügt werden (z.B. onboarding.md, operations.md).

### 🔹 6.4 Dokumentationen von Domains, Systems, APIs und Resources

Für Entitäten der Typen Domain, System, API und Resource sind Dokumentationen ebenfalls sinnvoll:

Domain
- Wofür steht diese Domain fachlich?
- Welche Systeme und Teams gehören dazu?
- Welche fachlichen und organisatorischen Leitplanken gelten?
- Welche gemeinsamen Standards sind relevant?

System
- Übergreifende Architekturdokumentation mit stärkerem Fokus auf:
  - Context
  - Building Blocks
  - Runtime View
  - weniger technische Details

API
- Wofür steht diese API fachlich?
- Welche Consumers nutzen sie und welche Anwendungsfälle werden abgedeckt?
- Welche Versionierungs- und Kompatibilitätsregeln gelten?

Resource
- Was stellt diese Ressource bereit?
- Wie wird sie genutzt (aus Sicht der Consumer)?
- Wer betreibt sie und wie erfolgt Support?
- Welche Leitplanken gelten?

Die Artefakte der Dokumentationen dieser Entitäten werden in den zugehörigen Domain bzw. Plattform Infrastruktur Repositories gespeichert. Abweichend zu Component Repositories gibt es dort jedoch nicht nur einen zentralen Ordner `docs`, sondern auch jeweils einen Ordner `docs` im Ordner der untergeordneten Entitäten.

Beispielstruktur einer Domain:

```
/domain-teilnehmerbetreuung/
  software-catalog-info.yaml
  domain-teilnehmerbetreuung-software-catalog-info.yaml
  docs/
    index.md
    mkdocs.yml
    overview.md
    ...
  systems/
    system-studieneinstieg/
      system-studieneinstieg-software-catalog-info.yaml
      docs/
        index.md
        mkdocs.yml
        architecture.md
        ...
    ...
  apis/
    api-anrechnungsservice-webapi/
      api-anrechnungsservice-webapi-software-catalog-info.yaml
      docs/
        index.md
        mkdocs.yml
        ...
    ...
  resources/
    resource-mariadb-shared/          # nur geteilte Resources
      resource-mariadb-shared-software-catalog-info.yaml
      docs/
        index.md
        mkdocs.yml
        ...
    ...
``` 

### 🔹 6.5 mkdocs.yml

Mit Techdocs verwenden wir MkDocs zur Erzeugung der Dokumentationsseiten aus den Markdown files. Die Konfiguration von MkDocs erfolgt über ein yaml File `mkdocs.yml`, welches wie index.md im Ordner `docs` vorhanden sein muss.

`site_name` ist zwingend erforderlich und wird mit dem Namen der Entität gefüllt. Im `nav` Bereich wird die globale Navigation für die Dokumentationsseiten konfiguriert. Hier ist mindestens index.md als Home sowie architecture.md für die Architekturdokumentation gesetzt. Weitere Dokumentationsartefakte sind hier individuell zu ergänzen. 

```yaml
site_name: Anrechnungsservice

nav:
  - Home: index.md
  - Architekturdokumentation: architecture.md

```

### 🔹 6.6 Einbindung von Dokumentationen in Techdocs

Um die Dokumentationen einer Entität in Techdocs einzubinden, muss der Pfad zu den Dokumentationsartefakten (in unserem Fall zum Ordner `docs`) im "catalog-info" YAML file in der `backstage.io/techdocs-ref` Annotation hinterlegt werden. Wenn der Ordner `docs` auf gleicher Ebene liegt, wie das "catalog-info" YAML file (bei einer Component Entität sollten beide im root liegen), genügt hier die Angabe von `dir:.`.    

```yaml
metadata:
  annotations:
    backstage.io/techdocs-ref: dir:.
```

---

## 7️⃣  Governance

### 🔹 7.1 Katalogimport

Die Owner der Entitäten sind für den Import und damit die Aufnahme der Entitäten in den Software Katalog verantwortlich. In der Umsetzung werden sie dabei durch das DevOps Plattform Team unterstützt (ggf. auch zukünftig durch erweiterte Funktionen zum automatisierten Katalogimport).

### 🔹 7.2 Pflege und Aktualität von Entities

Die Owner der Entitäten sind für die regelmäßige Pflege und damit Aktualität ihrer Entitäten im Software Katalog verantwortlich. Dies schließt auch die Dokumentationen mit ein. 

### 🔹 7.3 Betrieb, Wartung & Support der Backstage Plattform

Das DevOps Plattform Team betreibt und supportet die Backstage Plattform und ist für die Wartung des Systems verantwortlich.

---

## 8️⃣  YAML-Beispiele

Im folgenden sind einige YAML files aufgeführt, welche die in diesem Dokument beschriebenen Vorgaben gesamthaft verdeutlichen sollen.

### 🔹 8.1 Domain

```yaml
apiVersion: backstage.io/v1alpha1
kind: Domain
metadata:
  name: domain-teilnehmerbetreuung
  description: Geschäftsbereich für alle Systeme und Services rund um die Betreuung von Studierenden und Teilnehmern während ihres Studiums.
  annotations:
    backstage.io/techdocs-ref: dir:.
spec:
  owner: IT.Se.Domaene.Teilnehmer
```

### 🔹 8.2 System

```yaml
apiVersion: backstage.io/v1alpha1
kind: System
metadata:
  name: system-studieneinstieg
  description: System für die Verwaltung und Begleitung des Studieneinstiegs von neuen Studierenden.
  annotations:
    backstage.io/techdocs-ref: dir:.
  tags:
    - diga
    - anmeldung
spec:
  owner: IT.Se.Domaene.Teilnehmer
  domain: teilnehmerbetreuung
  lifecycle: production
```

### 🔹 8.3 Component (Service)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: component-anrechnungsservice
  description: Backend-Service für die Prüfung und Verwaltung von Anrechnungsanträgen.
  annotations:
    backstage.io/techdocs-ref: dir:.
    dev.azure.com/project-slug: BCW-Gruppe
  tags:
    - dotnet
    - aspnetcore
    - on-prem
spec:
  type: service
  owner: IT.Se.Domaene.Teilnehmer
  system: anrechnung
  lifecycle: production
  providesApis:
    - anrechnungsservice-webapi
  consumesApis:
    - elowebservice-api
  dependsOn:
    - resource:mariadb-anrechnungen
    - resource:sbq-anrechnung-requests
    - component:elowebservice
```

### 🔹 8.4 Component (Frontend)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: component-studieneinstieg-portal
  description: Web-Frontend für das Studieneinstiegsportal, über das neue Studierende ihre Onboarding-Schritte verfolgen können.
  annotations:
    backstage.io/techdocs-ref: dir:.
    dev.azure.com/project-slug: BCW-Gruppe
  tags:
    - angular
    - typescript
    - on-prem
spec:
  type: frontend
  owner: IT.Se.Domaene.Teilnehmer
  system: studieneinstieg
  lifecycle: production
  consumesApis:
    - studieneinstieg-api
  dependsOn:
    - component:studieneinstieg-backend
```

### 🔹 8.5 Component (Self-Contained System)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: component-pruefungsanmeldung
  description: |
    Self-Contained System für die Prüfungsanmeldung mit integriertem Frontend und Backend.
    Völlig autonomes System ohne Abhängigkeiten zu anderen Components der Domain.
  annotations:
    backstage.io/techdocs-ref: dir:.
    dev.azure.com/project-slug: BCW-Gruppe
  tags:
    - dotnet
    - angular
    - self-contained
    - on-prem
spec:
  type: self-contained-system
  owner: IT.Se.Domaene.Teilnehmer
  domain: lehrendenbetreuung-und-pruefungsmanagement  # Direkt an Domain, KEIN System
  lifecycle: production
  providesApis:
    - pruefungsanmeldung-api
  consumesApis:
    - teilnehmerverwaltung-api
  dependsOn:
    - resource:mariadb-pruefungen
    - resource:keyvault-bcw-prod
```

*Hinweis: Das SCS ist direkt der Domain zugeordnet (`spec.domain`), ohne eine zwischengeschaltete System-Ebene, da es völlig eigenständig ist.*

### 🔹 8.6 Component (Power App)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: component-raumbuchungs-app
  description: Power App für die Buchung von Räumen und Arbeitsmitteln durch Lehrende und Mitarbeiter.
  tags:
    - powerplatform
    - low-code
spec:
  type: powerapp
  owner: devops-platform-orchestration-automation
  lifecycle: production
  consumesApis:
    - raumbuchungs-api
  dependsOn:
    - resource:sharepoint-raumbuchungen
```

### 🔹 8.7 Component (Infrastructure)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: component-kibana
  description: Kibana-Instanz für Visualisierung und Exploration von Elasticsearch-Daten.
  annotations:
    backstage.io/techdocs-ref: dir:.
  tags:
    - elastic-stack
    - observability
    - on-prem
spec:
  type: infrastructure
  owner: devops-platform-orchestration-automation
  system: elastic-stack
  lifecycle: production
  providesApis:
    - kibana-api
  dependsOn:
    - resource:elasticsearch-prod
```

### 🔹 8.8 API (OpenAPI)

```yaml
apiVersion: backstage.io/v1alpha1
kind: API
metadata:
  name: api-anrechnungsservice-webapi
  description: REST API für die Verwaltung von Anrechnungsanträgen und -entscheidungen.
  annotations:
    backstage.io/techdocs-ref: dir:.
  tags:
    - rest
    - openapi
spec:
  type: openapi
  owner: IT.Se.Domaene.Teilnehmer
  system: anrechnung
  lifecycle: production
  definition:
    $text: https://dev.azure.com/BCW-Gruppe/AnrechnungsService/_git/AnrechnungsService?path=/openapi.yaml
```

*Hinweis: Die Spec wird per URL aus dem Component-Repository referenziert. Änderungen an der Spec (z.B. neue Endpoints) erfordern damit nur eine Anpassung im Component-Repository.*

### 🔹 8.9 API (AsyncAPI)

```yaml
apiVersion: backstage.io/v1alpha1
kind: API
metadata:
  name: api-digaonlineservice-mqapi
  description: Message Queue API für asynchrone Kommunikation mit dem DIGA Online Service über RabbitMQ.
  annotations:
    backstage.io/techdocs-ref: dir:.
  tags:
    - rabbitmq
    - async
    - messaging
spec:
  type: asyncapi
  owner: IT.Se.Domaene.Interessenten
  system: studieneinstieg
  lifecycle: production
  definition:
    $text: https://dev.azure.com/BCW-Gruppe/DigaOnlineService/_git/DigaOnlineService?path=/asyncapi.yaml
```

*Hinweis: Die Spec wird per URL aus dem Component-Repository referenziert. Änderungen an der Spec erfordern damit nur eine Anpassung im Component-Repository.*

### 🔹 8.10 Resource (Database)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: resource-mariadb-onlineanmeldungen
  description: MariaDB-Datenbank für die Speicherung von Online-Anmeldungen und Interessentendaten.
  annotations:
    backstage.io/techdocs-ref: dir:.
  tags:
    - mariadb
    - database
    - on-prem
spec:
  type: database
  owner: IT.Se.Domaene.Interessenten
  system: studieneinstieg
  lifecycle: production
  dependsOn:
    - resource:mir-dev-mgmt-01
```

### 🔹 8.11 Resource (Queue)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: resource-sbq-anrechnung-requests
  description: Azure Service Bus Queue für eingehende Anrechnungsanfragen.
  tags:
    - azure
    - servicebus
    - queue
spec:
  type: queue
  owner: IT.Se.Domaene.Teilnehmer
  system: anrechnung
  lifecycle: production
```

### 🔹 8.12 Resource (Observability)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: resource-elasticsearch-prod
  description: Produktions-Elasticsearch-Cluster für Logging, Monitoring und Suche.
  annotations:
    backstage.io/techdocs-ref: dir:.
    monitoring/dashboard-url: https://kibana.bcw.local/app/dashboards
  tags:
    - elasticsearch
    - observability
    - on-prem
spec:
  type: observability
  owner: devops-platform-orchestration-automation
  system: elastic-stack
  lifecycle: production
  dependsOn:
    - resource:mir-prod-infra-01
```

### 🔹 8.13 Resource (Server)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: resource-mir-dev-mgmt-01
  description: Virtueller Server für Development-Umgebung und Management-Tools.
  tags:
    - vm
    - windows-server
    - on-prem
spec:
  type: server
  owner: devops-platform-orchestration-automation
  lifecycle: production
```

### 🔹 8.14 Resource (Vault)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Resource
metadata:
  name: resource-keyvault-bcw-prod
  description: Azure Key Vault für zentrale Verwaltung von Secrets, Zertifikaten und Schlüsseln.
  tags:
    - azure
    - security
    - secrets
spec:
  type: vault
  owner: devops-platform-orchestration-automation
  lifecycle: production
```

### 🔹 8.15 Location (Domain)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Location
metadata:
  name: domain-teilnehmerbetreuung-catalog
  description: Backstage Katalog für die Domäne Teilnehmerbetreuung.
spec:
  type: url
  targets:
    # Domain
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/domain-teilnehmerbetreuung?path=/domain-teilnehmerbetreuung-software-catalog-info.yaml
    # Systems
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/domain-teilnehmerbetreuung?path=/systems/system-studieneinstieg/system-studieneinstieg-software-catalog-info.yaml
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/domain-teilnehmerbetreuung?path=/systems/system-anrechnung/system-anrechnung-software-catalog-info.yaml
    # APIs (alle APIs der Domäne, Spec wird per URL aus dem jeweiligen Component-Repo referenziert)
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/domain-teilnehmerbetreuung?path=/apis/api-anrechnungsservice-webapi/api-anrechnungsservice-webapi-software-catalog-info.yaml
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/domain-teilnehmerbetreuung?path=/apis/api-digaonlineservice-mqapi/api-digaonlineservice-mqapi-software-catalog-info.yaml
    # Shared Resources (nur von mehreren Components gemeinsam genutzte Resources)
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/domain-teilnehmerbetreuung?path=/resources/resource-mariadb-shared/resource-mariadb-shared-software-catalog-info.yaml
```

### 🔹 8.16 Location (Plattform Infrastruktur)

```yaml
apiVersion: backstage.io/v1alpha1
kind: Location
metadata:
  name: platform-infrastructure-catalog
  description: Backstage Katalog für zentrale Plattform- und Infrastrukturressourcen.
spec:
  type: url
  targets:
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/platform-resources?path=/systems/system-elastic-stack/system-elastic-stack-software-catalog-info.yaml
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/platform-resources?path=/systems/system-azure-devops/system-azure-devops-software-catalog-info.yaml
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/platform-resources?path=/components/component-elasticsearch/component-elasticsearch-software-catalog-info.yaml
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/platform-resources?path=/components/component-kibana/component-kibana-software-catalog-info.yaml
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/platform-resources?path=/resources/resource-elasticsearch-prod/resource-elasticsearch-prod-software-catalog-info.yaml
    - https://dev.azure.com/BCW-Gruppe/Backstage/_git/platform-resources?path=/resources/resource-mir-dev-mgmt-01/resource-mir-dev-mgmt-01-software-catalog-info.yaml
```

### 🔹 8.17 Vollständiges Beispiel: Component mit allen Beziehungen

```yaml
apiVersion: backstage.io/v1alpha1
kind: Component
metadata:
  name: component-digaonlineservice
  description: |
    Zentraler Service für die Verarbeitung von Online-Anmeldungen neuer Interessenten.
    Verarbeitet Anmeldungen über verschiedene Kanäle und speichert diese in der MariaDB.
  annotations:
    backstage.io/techdocs-ref: dir:.
    dev.azure.com/project-slug: BCW-Gruppe
    dev.azure.com/build-definition: digaonlineservice-ci
  tags:
    - dotnet
    - aspnetcore
    - messaging
    - on-prem
spec:
  type: service
  owner: IT.Se.Domaene.Interessenten
  system: studieneinstieg
  domain: interessentenakquise-und-betreuung
  lifecycle: production
  providesApis:
    - digaonlineservice-webapi
    - digaonlineservice-mqapi
  consumesApis:
    - notification-service-api
  dependsOn:
    - resource:mariadb-onlineanmeldungen
    - resource:sbq-onlineanmeldung-events
    - resource:keyvault-bcw-prod
    - component:notification-service
```

---

*Stand: 28. Februar 2026*
*Erstellt für die Einführung von Backstage und Techdocs in der BCW‑Softwarelandschaft.*

