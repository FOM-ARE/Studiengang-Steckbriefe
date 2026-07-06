# IT.SE Coding Guidelines

**Version:** 1.0
**Stand:** Februar 2025

---

## Einleitung

Coding Guidelines tragen dazu bei, dass der Code lesbarer, wartbarer, fehlerfreier und sicherer wird, was letztlich die Qualität der Software und die Effizienz des Entwicklungsteams erhöht. Durch die Einhaltung von Coding Guidelines wird der Code zukunftssicherer und nachhaltiger gestaltet.

Zugrundeliegende Architektur-Entscheidung: #2024.007 - Coding Guidelines

## Ziele

### Verbesserung der Lesbarkeit und Verständlichkeit

Konsistenz: Einheitliche Regeln erleichtert es Entwicklern, den Code zu verstehen und zu bearbeiten, unabhängig davon, wer ihn ursprünglich geschrieben hat.

Struktur: Gut strukturierter Code hilft dabei, die Funktionsweise und den Zweck des Codes schnell zu erfassen.

Namen: Sprechende Namen für alle Code Komponenten (Variablen, Methoden, Klassen, Assemblies, Projekte).

### Erhöhung der Wartbarkeit

Einfachere Fehlerbehebung: Konsistenter und gut strukturierter Code erleichtert das Finden und Beheben von Fehlern.

Erweiterbarkeit: Sauberer Code kann leichter angepasst und erweitert werden, wenn sich Anforderungen ändern.

### Förderung der Zusammenarbeit

Teamarbeit: Ein gemeinsamer Satz von Regeln sorgt dafür, dass alle Teammitglieder auf dieselbe Weise arbeiten, was die Zusammenarbeit und den Code-Review-Prozess erleichtert.

Einarbeitung neuer Entwickler: Neue Teammitglieder können sich schneller einarbeiten, wenn sie auf konsistenten und gut dokumentierten Code stoßen.

Diese Guidelines sollen dazu dienen den Austausch über unser Metier zu fördern. Diskutiert und erweitert diese Regeln.

### Vermeidung von Fehlern

Standardisierte Praktiken: Durch die Einhaltung bewährter Praktiken und Standards können häufige Fehler vermieden werden.

Robustheit: Applikationen sollten im Fehlerfall stabil sein.

### Effizienz und Produktivität

Durch klare Richtlinien für Effizienz und Produktivität können Teams hochwertigen Code schneller und ressourcenschonender entwickeln, was die langfristige Wartbarkeit und Skalierbarkeit der Software verbessert.

### Einhaltung von Best Practices

Qualitätsstandards: Richtlinien basieren oft auf bewährten Methoden, die die Qualität des Codes sicher stellen.

---

## Code Smells

### Duplicated Code

Damit ist nicht nur gleicher/kopierter Code gemeint, sondern auch gleiche Funktion mit ähnlichem Code. Damit erhöht sich der Aufwand in der Wartung (beim Ändern) und auch beim Schreiben der Tests. Damit steigt auch die Fehleranfälligkeit, weil man an einer Stelle den Fehler korrigiert, aber an der anderen Stelle vergisst.

### Lange Methode

Zu langer Code vergrößert die Wahrscheinlichkeit, dass man die Funktion/Methode nicht oder falsche interpretiert. Damit steigt auch die Gefahr bei Änderungen einen Fehler einzubauen. Die Wiederverwendbarkeit wird erschwert, weil meistens diese Methoden zu spezifisch sind, um dies zu gewährleisten.

### Lange Parameterliste

Änderungen an der Signatur der Methode bedingt immer auch eine Anpassung der Aufrufe. Letztendlich ist aber die Lesbarkeit verbessert, wenn man anstelle einer langen Parameterliste stattdessen eine eigene Klasse dafür verwendet.

### Lange Code-Zeilen

Lange Codezeilen verstecken einen Teil des Codes, der dadurch nicht auf den ersten Blick erfasst wird. Die Lesbarkeit und das Verständnis wird durch lange Zeilen erschwert.

### Schachtelung von Methodenaufrufen

Diese Form erhöht die kognitive Last und erschwert das Verständnis. An dieser wird auch die Reihenfolge der Abarbeitung verkehrt (das Innere zuerst anstelle von Links nach Rechts). Zusätzlich ist es schwieriger zu debuggen, weil potenziell Ergebnisse der inneren Funktionen verschwinden und Breakpoints nur schwer zu setzen sind.

### Große Klasse

Bei groÄen Klassen besteht die Gefahr mehrere Aspekte miteinander zu vermischen (SRP).

### Feature-Neid

Beschreibung: Eine Methode verwendet mehr Methoden und Daten einer anderen Klasse als ihrer eigenen.

Behebung: Verschiebe die Methode in die Klasse, auf deren Daten sie zugreift.

### Switch-Anweisungen

Beschreibung: Häufige Verwendung von switch-Anweisungen zur Verzweigung der Logik.

Behebung: Verwende Polymorphismus, um die Logik auf unterschiedliche Klassen zu verteilen.

### Spekulative Allgemeinheit

Beschreibung: Code ist verallgemeinert, um zukünftige Anforderungen zu berücksichtigen, die möglicherweise nie eintreten.

Behebung: Entferne unnötige Abstraktionen und konzentriere dich auf die aktuellen Anforderungen.

### Boolean als Parameter

Methode macht mehrere Sachen

### Unangemessene Intimität

Beschreibung: Klassen kennen zu viele Details über die internen Strukturen anderer Klassen.

Behebung: Reduziere die Abhängigkeiten zwischen den Klassen und stelle sicher, dass sie nur über öffentliche Schnittstellen kommunizieren

---

## Guidelines

### Einhaltung von Best Practices

Namenskonventionen:

Variablen und Funktionen:

Verwendet camelCase für Variablen und

Verwende PascalCase für Klassennamen, Methoden und Konstanten

Nutze aussagekräftige Namen, die den Zweck der Variable oder Funktion klarmachen.

Private Properties und Felder fangen mit _ an.

Vermeide Sonderzeichen (z.B. ä, ü usw.)

### Prinzipien

- DRY (Don't Repeat Yourself):

Vermeide Redundanzen im Code, indem du wiederverwendbare Funktionen und Module erstellst.
- YAGNI (You Ain't Gonna Need It):

Implementiere nur die Funktionalitäten, die aktuell benötigt werden. Vermeide überflüssige Features.
- KISS (Keep It Simple, Stupid):

Halte den Code so einfach wie möglich. Vermeide unnötige Komplexität.
- SLA (Single Level of Abstraction)

In einem Codeblock sollen alle Anweisungen auf derselben Abstraktionsebene gehalten werden.
- PLS (Principle Of Least Surprise)

Eine Komponente eines Systems sollte sich so verhalten, wie die meisten Benutzer es erwarten.
- composition over inheritance
- SOLID:

SRP (Single Responsibility Principle)

Es sollte nie mehr als einen Grund geben, eine Komponente zu ändern.

Open Close Prinzip

Module sollten für Erweiterungen geöffnet, für Änderungen jedoch geschlossen sein.

Liskovsches Substitutionsprinzip

Untertypen müssen für ihre Basistypen ersetzbar sein.

Interface Segregation

Stelle keine Methoden zur Verfügung, die er nicht verwendet werden.

Dependancy Inversion

High-Level-Komponenten sollten nichts von Low-Level- Komponenten importieren. Beide sollten von Abstraktionen (z. B. Schnittstellen) abhängen.
Abstraktionen sollten nicht von Details abhängen. Details (konkrete Implementierungen) sollten von Abstraktionen abhängen.

http://principles-wiki.net/principles:start

### Clean Code

Als "Sauber" wird Code bezeichnet, der intuitiv verständlich ist.

Guter Code

Einfacher und geradliniger Code, der von anderen Entwicklern gut gelesen und verbessert werden kann, mit dem Ziel stabile und effizient wartbare Programme zu entwickeln.

Daraus ergibt sich eine kürzere Entwicklerzeit bei Funktionserweiterungen und Fehlerbehebungen.

Gute Software besteht alle Tests.

Die Qualität bemisst sich unter der Perspektive, dass 80% der Lebensdauer einer Software auf den Wartungszeitraum entfällt.

Unabhängig von den Clean-Code-Prinzipien, ist es auch wichtig sich als Entwickler um die Warnungen beim Build-Vorgang zu kümmern. Diese deuten sehr häufig auf (vermeidbare) zukünftige Probleme hin, wie zum Beispiel als "Obsolete" markierte Methoden/Properties und auch Sprach-Features zu sich in nicht allzu ferner Zukunft ändern und dann unweigerlich, überraschend zu Fehlern mutieren.

https://clean-code-developer.de/

### Projektstruktur

Wir entwickeln unsere Applikationen auf Basis einer Projektvorlage. Siehe hierzu auch: Anwendung der Projektvorlage

Jede Klasse sollte in einer eigenen Datei liegen, deren Name mit dem Klassennamen übereinstimmt.

Dateien sollten in logischen Verzeichnissen organisiert sein, die den Paketstrukturen entsprechen.

Clean Architecture:

Presenter: Ist die Stelle an der das Ergebnis zur Anzeige aufbereitet wird.

Interactor: Zentrale Schaltstelle, in der der Ablauf eines Prozesses definiert wird.

Infrastructure: Externe Ressourcen, inkl. Dateizugriffen, werden hier eingebunden.

### Versions-Kontrolle

Versionskontrolle ist ein unverzichtbares Werkzeug in der Softwareentwicklung, das es ermöglicht, den gesamten Verlauf von Codeänderungen nachzuverfolgen und zu verwalten. Hier sind die Hauptgründe, warum Versionskontrolle wichtig ist:

1. Nachvollziehbarkeit: Jede Änderung am Code wird erfasst, einschließlich wer sie gemacht hat, wann sie gemacht wurde, und warum. Dadurch kann der Entwicklungsverlauf lückenlos nachvollzogen werden.
2. Zusammenarbeit: Mehrere Entwickler können gleichzeitig am gleichen Projekt arbeiten, ohne sich gegenseitig in die Quere zu kommen. Versionskontrollsysteme (wie Git) ermöglichen es, Änderungen zusammenzuführen und Konflikte zu lösen.
3. Rückverfolgbarkeit: Fehler können leichter identifiziert und behoben werden, da frühere Versionen des Codes jederzeit wiederhergestellt werden können.
4. Sicherheitsnetz: Falls neue Änderungen Probleme verursachen, kann der Code auf eine frühere, funktionierende Version zurückgesetzt werden, was das Risiko von Datenverlust minimiert.
5. Verzweigung und Experimentation: Entwickler können neue Features oder Experimente in isolierten "Branches" ausprobieren, ohne den Hauptcode zu beeinträchtigen. Dies fördert Innovation und flexibles Arbeiten.

Insgesamt stellt die Versionskontrolle sicher, dass der Entwicklungsprozess geordnet, nachvollziehbar und sicher abläuft.

#### Anti-Pattern

Neben der Ordnung auf der Festplatte, ist die gleiche Übersichtlichkeit und Ordnung im Git für jeden Entwickler sehr hilfreich.
Ein weniger bekanntes Feature von Git sind z.B. "Sub-Modules". Damit kann man in ein Repository weitere Repos auch aus anderen Quellen hinzufügen, ohne die dazugehörigen Dateien im eigenen Repository mit einzuchecken. Problem ist dabei eine Abhängigkeit von einem anderen (fremden) Projekt hinzukommt, bei der man leicht einen Zustand beim Build erreicht, bei dem der Output nicht reproduzierbar ist. Das widerspricht eigentlich dem Grundgedanken der Version-Kontrolle, einen bestimmten Zustand, zu jederzeit wiederherstellen zu können. Deswegen ist es zu vermeiden "Sub-Modules" zu verwenden.

#### Dateien im Git

Auch wenn es klar sein sollte, in ein Repository sollen keine Dateien der IDE committed werden, oder Dateien, die als Ergebnis beim Build erstellt werden (in den meisten Fällen bin/obj etc.)

#### Branch-Schema

Wir wollen vermeiden, dass unbeabsichtigt Features und andere Änderungen in den Produktiven Code gelangen oder auch schon in der Staging-Umgebung ausgeführt werden.

Gleichzeitig möchten wir es jedem Entwickler vereinfachen, sich im Code anderer Teams zurechtzufinden. Dazu trägt die Projektstruktur und Organisation bei, aber auch ein gemeinsames Verständnis davon, wie Branches benannt und erzeugt werden aber auch wieder gemerged werden.

Das im Folgenden vorgestellte Schema bedeutet auf den ersten Blick, dass mehr Pull-Requests gestellt werden (für den gleichen Branch), stellt aber sicher, dass keine Änderungen ungewollt in produktiven Code gelangen.

Prinzipiell sollen alle Änderungen vom Master/Main-Branch ausgehend in eigenen Bugfix- oder Feature-Branches vorgenommen werden. Die jeweiligen Pullrequests werden dann je nach Entwicklungsfortschritt für den Development-, Staging- oder Main-Branch gestellt und gemerged.

Es soll dabei vermieden werden die feature/Bugfix-Branches vom Development- oder Staging-Branch ausgehend abzuzweigen, weil damit auch schon andere Änderungen hier mit einfließen, die zwischenzeitlich gemerged wurden und dann potenziell auch durch anschließendes Mergen im Master-Branch landen würden.

#### Pull-Requests

Spätestens für die Branches "main" und "staging" sind Pull-Requests verpflichtend, die von einem 2. Entwickler akzeptiert werden müssen. Ein Commit in diese beiden Branches ist nicht möglich. Mit einem Pull-Request sollte ein Azure-Ticket verknüpft sein. Im Pull-Request werden nicht nur formale Kriterien geprüft, sondern auch inhaltliche, logische Aspekte (auch Performance). Der Pull-Request muss einen aussagefähgen Titel bekommen und eine Beschreibung, die helfen den Context und Inhalt des Pull-Requests zu verstehen.

### Musterlösungen/Entwurfsmuster/Design Patterns

Die folgenden Design Patterns sollen als Hilfsmittel verstanden werden, um sauberen Code (siehe Clean Code) zu schreiben (z.B. KISS Prinzip) und sind Vorschläge, die jeder Entwickler kennen sollte.

#### Erzeugungsmuster (Creational Patterns)

bieten flexible Mechanismen zur Objekterstellung, die über die herkömmliche Instanziierung mit dem new-Operator hinausgehen und die Wiederverwendbarkeit und Wartbarkeit des Codes verbessern.

Factory Method: Definiert eine Schnittstelle zur Erstellung von Objekten, lässt aber die Unterklassen entscheiden, welche Klasse instanziiert wird.

#### Strukturmuster (Structural Patterns)

bieten Lösungen zur effektiven Strukturierung und Komposition von Klassen und Objekten, um die Flexibilität, Erweiterbarkeit und Wartbarkeit von Software zu verbessern.

Adapter: Ermöglicht es Objekten mit inkompatiblen Schnittstellen zusammenzuarbeiten, indem eine "Adapter"-Klasse eine Schnittstelle in eine andere umwandelt.

Facade: Bietet eine vereinfachte Schnittstelle zu einer komplexen Subsystemsammlung.

MVC: teilt die Verantwortlichkeiten zwischen Model (Daten und Geschäftslogik), View (Darstellung) und Controller (Präsentationslogik und Benutzerinteraktion) auf. Der Controller handhabt die Benutzeraktionen und aktualisiert das Modell und die Ansicht entsprechend.

Repository Pattern: Der Zugriff auf Datenquellen wird abstrahiert und zu zentralisiert. Es fördert eine klar definierte Schnittstelle zwischen der Geschäftslogik der Anwendung und den Datenzugriffsschichten.

#### Verhaltensmuster (Behavioral Patterns)

bieten Lösungen zur effizienten Kommunikation und Interaktion zwischen Objekten und zur Organisation des Verhaltens von Softwarekomponenten.

Template Method: Definiert das Skelett eines Algorithmus in einer Methode, wobei die Schritte des Algorithmus durch Unterklassen implementiert werden.

### Verbesserung der Lesbarkeit und Verständlichkeit

Das Vokabular der Fachabteilungen sollte in Kombination mit technischen Begriffen verwendet werden. z.B. GetNote(personenId);

Benutze sprechende Namen. Wenn es schwer fällt einen Namen zu finden, macht die Komponente möglicherweise zu viel. (vgl. SRP)

Implementiere kurze Methoden. Mehr als 15 Zeilen sollten zum Nachdenken führen. (vgl. SLA)

Nutze wenige Parameter. Große Parameterlisten in Typen kapseln.

Erstelle kleine Klassen die genau eine Sache, diese aber vollständig, verantworten.

Vermische keine Logik mit der Datenhaltung.

Kommentierung: Kommentiere so wenig wie möglich, sondern schreibe deinen Code intuitiv verständlich. Kommentiere das Warum und niemals das Wie.

Unnötige oder gar falsche Kommentare halten beim Lesen auf. Der Code sollte so klar und deutlich sein, dass er möglichst ohne Kommentare auskommt.

Auskommentierter Code darf nicht eingecheckt werden.

### Erhöhung der Wartbarkeit

#### Open-Closed Prinzip

Schreibe bei Bedarf deine Module so, dass sie möglichst erweiterbar sind, ohne den Code ändern zu müssen. (Open-Closed Prinzip)

#### Unit-Tests

Unit-Tests sind ein mehrdimensionaler und wichtiger Bestandteil der Softwareentwicklung.

Als guter Software-Entwickler ist man dazu verpflichtet, den geschriebenen Code auch "auszuprobieren". In vielen Fällen neigt man dazu den neuen Code einfach laufen zu lassen und zu sehen, ob der geschriebene Code so funktioniert, wie erwartet.
Je komplexer die dazu erforderlichen Vorbereitungen werden, desto schlechter wird die Wiederholbarkeit dieses âAusprobierensâ. Allerspätestens an diesem Punkt ist es mehr als sinnvoll, das Vorgehen zu systematisieren und zu automatisieren.

Damit ist man im einfachsten Fall bei Unit-Tests angekommen. Unit-Tests stellen nicht nur sicher, dass zur Entwicklungszeit die erkannten Probleme/Fehlerfälle reproduzierbar sind, sondern stellen auch für die Zukunft sicher, dass ein Verhalten, dass heute implementiert worden ist, nicht unbeabsichtigt verändert wird. Ohne Unit Tests verkommt auch der Code!

Zusätzlich ist es auch im Sinne der Dokumentation hilfreich. Einen Unit-Test ist auch wie ein Beispiel für die Verwendung einer Funktion/Klasse zu sehen. Man gibt so anderen Entwicklern einen guten und hilfreichen Hinweis über den Einsatz der getesteten Funktionen.

Also: Schreibe Unit Tests für alle Komponenten die Business-Logik enthält.

Code Coverage: Strebe eine Code Coverage von mindestens 80% an.

Automatisierte Tests: Setze automatisierte Tests ein, um die Funktionsweise des Codes sicherzustellen.

#### Logging

##### Warum loggen wir?

Logging ist ein wesentlicher Bestandteil jeder Softwareanwendung. Es dient mehreren Zwecken:

- Fehlerdiagnose: Logs helfen uns, Fehler und Probleme in der Anwendung schnell zu identifizieren und zu beheben.
- Nachvollziehbarkeit: Sie ermöglichen es, die Abfolge von Ereignissen zu verstehen, insbesondere wenn es um die Nachverfolgung von Transaktionen oder Benutzeraktivitäten geht.
- Sicherheitsüberwachung: Logs sind unverzichtbar, um sicherheitsrelevante Ereignisse zu überwachen, wie z.B. fehlgeschlagene Anmeldeversuche oder verdächtige Aktivitäten.
- Performance-Monitoring: Mit Hilfe von Logs können wir Engpässe und ineffiziente Prozesse identifizieren, die die Performance der Anwendung beeinträchtigen.

##### Was loggen wir?

Die Art der Informationen, die geloggt werden sollen, hängt von der spezifischen Anwendung und ihren Anforderungen ab. Hier sind einige allgemeine Richtlinien:

- Fehler und Ausnahmen: Jede Exception, die in der Anwendung auftritt, sollte mit allen relevanten Informationen (Stack Trace, Kontext) geloggt werden.
- Systemereignisse: Start und Stopp der Anwendung und andere relevante Systemereignisse sollten erfasst werden.
- Performance-Daten: Zeitpunkte und Dauer wichtiger Operationen sollten geloggt werden, um die Performance der Anwendung zu überwachen.

##### Was wir vermeiden sollten:

- Vertrauliche Daten: Niemals sensible Daten wie Passwörter, vollständige Kreditkartennummern oder persönliche Identifikationsnummern in Logs speichern.
- ÄbermäÄiges Logging: Zu viele Logs können das System überlasten und das eigentliche Problem verdecken. Logge nur das, was wirklich relevant ist.

##### Welches Log Level soll für welchen Fall genutzt werden?

- Die Verwendung von Log Levels ermöglicht es uns, die Dringlichkeit und den Zweck des geloggten Ereignisses zu kategorisieren. Hier sind die gängigsten Log Levels und wann sie genutzt werden sollten:
- TRACE:

Wann nutzen: Um extrem detaillierte Informationen zu protokollieren, die hauptsächlich für die Diagnose von Problemen während der Entwicklung verwendet werden.
Beispiele: Anfang und Ende von Methodenaufrufen, detaillierte Protokolle interner Algorithmen.
- DEBUG:

Wann nutzen: Zum Debuggen während der Entwicklungs- und Testphase. Es liefert umfangreiche Informationen, die für die Fehlerbehebung nützlich sind, aber in der Produktion deaktiviert sein sollten.
Beispiele: Zustandsinformationen, detaillierte Ablaufverfolgung, Eingabewerte von Methoden.
- INFORMATION:

Wann nutzen: Um den normalen Betrieb der Anwendung zu protokollieren. Dies sind Informationen, die in einer Produktionsumgebung standardmäßig erfasst werden.
Beispiele: Start und Stopp der Anwendung, erfolgreiche Verarbeitung von Anfragen, Konfigurationsänderungen.
- WARNING:

Wann nutzen: Wenn ein unerwartetes Ereignis auftritt, das nicht kritisch ist, aber möglicherweise auf ein zukünftiges Problem hinweisen könnte.
Beispiele: Fallback-Mechanismen, langsame Abfragen, ungewöhnlich lange Antwortzeiten, ungültige aber nicht kritische Eingaben.
- ERROR:

Wann nutzen: Um Fehler zu protokollieren, die das Fortsetzen eines Prozesses verhindern. Diese Ereignisse erfordern Aufmerksamkeit, beeinträchtigen aber nicht unbedingt die gesamte Anwendung.
Beispiele: Ausnahmebehandlungen, fehlgeschlagene Datenbankabfragen, unerwartete Zustände.
- CRITICAL:

Wann nutzen: Wenn ein kritischer Fehler auftritt, der die Anwendung oder einen wichtigen Teil davon zum Absturz bringt.
Beispiele: Unbehandelte Ausnahmen, Fehler, die die Anwendung nicht mehr korrekt ausführen lassen.

##### An welcher Stelle soll geloggt werden?

1. Global Exception Handling (Middleware)

- Wo: In der Middleware oder im GlobalExceptionHandler.
- Warum: Alle unhandled Exceptions, die in der Anwendung auftreten, sollten hier abgefangen und geloggt werden. Dies stellt sicher, dass kritische Fehler protokolliert werden, selbst wenn sie an anderer Stelle nicht behandelt wurden.

1. Controller-Aktionen

- Wo: Am Anfang und Ende von Controller-Aktionen.
- Warum: Es ist nützlich, den Eingang und Ausgang jeder HTTP-Anfrage zu protokollieren. Dadurch können Anfragen nachverfolgt werden, was besonders bei der Diagnose von Problemen hilfreich ist.

1. Business-Logic

- Wo: In den Methoden der Business-Logic.
- Warum: Hier wird die Kernlogik der Anwendung verarbeitet. Es ist wichtig, hier wichtige Schritte, Entscheidungen oder Fehler zu protokollieren, um die Nachvollziehbarkeit der Geschäftslogik zu gewährleisten.

1. Datenzugriffsschicht (Repository)

- Wo: Beim Zugriff auf die Datenbank.
- Warum: Datenbankoperationen sind oft eine Quelle von Leistungsproblemen oder Fehlern. Das Loggen von Abfragen, die viel Zeit in Anspruch nehmen, oder von Verbindungsfehlern ist entscheidend.

1. Externe API-Aufrufe

- Wo: Vor und nach Aufrufen externer APIs oder Services.
- Warum: Externe Aufrufe können zu Verzögerungen führen oder fehlschlagen. Es ist wichtig, diese zu überwachen und etwaige Fehler oder lange Antwortzeiten zu protokollieren.

1. Sicherheitskritische Bereiche

- Wo: Bei sicherheitsrelevanten Vorgängen wie Authentifizierung, Autorisierung und Zugriffskontrolle.
- Warum: Sicherheitsereignisse müssen sorgfältig protokolliert werden, um unautorisierte Zugriffe oder potenzielle Sicherheitslücken zu erkennen.

Applikationen sollten im Fehlerfall nach ELC loggen.

### Förderung der Zusammenarbeit

Ein wichtiger Aspekt beim täglichen Programmieren ist auch ein regelmäßiges Code-Review. Dabei geht nicht nur um die Vermeidung von Fehlern, sondern auch um das Weitergeben von Wissen über den geschriebenen Code und den fachlichen Hintergrund. Ein Code-Review soll aber auch dazu dienen, einen gemeinsamen Qualitäts-Standard zu finden und stetig zu verbessern.

An dieser Stelle findet dann auch ein Austausch über die Auslegung von Clean-Code und Clean-Architecture statt. Es ist wichtig, für eine schnelle Einarbeitung in fremden Code das gleiche Verständnis von Struktur und Anordnung und Namensgebung im Code zu haben.

### Vermeidung von Fehlern

Sicherheitsrichtlinien

#### Eingaben validieren:

Validiert alle Eingaben, bevor sie weiterverarbeitet oder in die Datenbank geschrieben werden. Je eher ungültige oder nicht zu verarbeitende Daten erkannt werden, desto schneller kann der Anwender darüber informiert werden, möglicherweise bevor eine spätere, nachgelagerte, manuelle Fehlerkorrektur vom Anwender vorgenommen werden muss. Der Aspekt Validierung sollte auch unabhängig von einer evtl. vorhandenen Eingabe-Prüfung in der Oberfläche erfolgen.
Grundsätzlich sollte man im Backend davon ausgehen, dass sich das Frontend ändern kann und von einem anderen Team erstellt wird oder einer Fremdfirma ausgeführt werden kann. Damit verliert man den Einfluss auf die Validierung etwaiger Daten.

#### SQL Parameterized Queries:

Nutze parameterisierte Abfragen, um SQL-Injection zu verhindern. Dieser Aspekt ist beim Einsatz von EF zwar nicht so präsent, aber falls dennoch SQL direkt ausgeführt werden sollte, muss sichergestellt werden, dass die Parameter keinen Einfluss auf das Statement an sich haben.

#### URL-Parameter:

Im Grunde gilt das gleiche bei URL-Parametern, wie bei SQL. URL-Parameter sind gleichermaßen eine häufige Quelle für Fehler. Gerade bei Zeichenketten ist vorher unbedingt sicherzustellen, dass die Informationen URL-Encodiert werden, auch im Controller bei der Verarbeitung muss garantiert sein, dass die Informationen wieder korrekt dekodiert werden.  Auch das korrekte Verarbeiten von NULL-Werten ist hier häufig problematisch.
Man sollte vermeiden URL-Parameter zu verwenden, oder nur solche Informationen, die kein besonderes Handling erfordern (z.B.: int, Guid) und erwiesenermaÄen nicht NULL sein können.

#### Ressourcen-Zugriffe:

Alle Ressourcen-Zugriffe sollten nach Möglichkeit nicht innerhalb von Schleifen stattfinden. Dies hat in den meisten Fällen eine erhebliche Auswirkung auf die Performance und sind meistens problemlos zu vermeiden. Zu diesen Ressourcen zählen insbesondere Datenbank- und HTTP-Aufrufe. Durch Dependency-Injection und ungünstiger Verschachtelung von Aufrufen ist dies nicht in jedem Fall offensichtlich.

Auch der das aktuelle Datum ist als eine Ressource zu betrachten. Sobald dies innerhalb der Business-Logik verwendet wird (DateTime.Today oder DateTime.Now), ist diese Klasse mit Unit-Tests schlechter testbar, als bei Äbergabe des passen Datums/Zeitpunkts als Parameter, insofern ist die Verwendung von DateTime.Now etc. nicht ratsam.

#### Compiler-Warnungen

Die Warnungen beim Kompilieren dürfen nicht ignoriert werden. Mitunter wird z.B. auf abgekündigte Funktionen hingewiesen. Auch potenziell unsaubere Codestellen werden aufgelistet. Idealerweise gibt es beim Build-Vorgang keine Warnungen. Warnungen sollten auf keinen Fall durch z.B. #pragma ignoriert werden, man muss sich um das originäre Problem kümmern, nicht um die Warnung.

#### Sensitive Daten:

Speichere keine sensiblen Daten unverschlüsselt. Verwende geeignete Verschlüsselungsmethoden. Grundsätzlich sollte kein Endpunkt unverschlüsselt aufgerufen werden (HTTP anstelle HTTPS). HTTPS ist keine technische Herausforderung, die nicht erfüllt werden kann. Auch der Zugriff auf Endpunkte über das interne Netzwerk sollte nicht über HTTP laufen.
Gerade beim Logging muss man diesen Aspekt berücksichtigen, ggf. sind sensible Daten nicht oder nur anonymisiert zu protokollieren.

---

## Nutzung von KI in der Softwareentwicklung

Wir nutzen KI-Unterstützung in der Softwareentwicklung, z.B. durch Github Copilot. Dies hat jedoch keinen Einfluss auf die Gültigkeit der hier formulierten Coding Guidelines. Auch KI-generierter Code, oder mit KI-Unterstützung erzeugter Code muss entsprechend den gemeinsamen Guidelines folgen. Die Verantwortung für die Qualität der gesamten Code-Basis liegt beim zuständigen Entwicklungs-Team, unabhängig davon, ob vollständig durch Menschen oder ganz oder teilweise durch KI erzeugt.

---

## Weiterführende Informationen

### Prinzipien

http://principles-wiki.net/principles:start

[SOLID-Prinzipien](https://bcwfom.sharepoint.com/:w:/r/sites/TechnischeDokumentation/Freigegebene%20Dokumente/Technische%20Dokumentation/Software-Architektur/Grundlagenwissen/Software-Design/SOLID-Prinzipien.doc?d=w4237581b1d394e609d48b52ba018d3e3&csf=1&web=1&e=PEpTGU)

### Clean Code

[Clean Code](https://bcwfom.sharepoint.com/:f:/r/sites/TechnischeDokumentation/Freigegebene%20Dokumente/Technische%20Dokumentation/Software-Architektur/Grundlagenwissen/Software-Design/Clean%20Code?csf=1&web=1&e=YfRe23)

### Projektstruktur

[Anwendung der Projektvorlage](https://bcwfom.sharepoint.com/:f:/r/sites/TechnischeDokumentation/Freigegebene%20Dokumente/Technische%20Dokumentation/Software-Architektur/Architekturvorgaben/Technische%20Basis/Technische%20Umsetzung/Projektstruktur/Anwendung%20der%20Projektvorlage?csf=1&web=1&e=7bKKqZ)

### Clean Architecture

[Clean Architecture](https://bcwfom.sharepoint.com/:w:/r/sites/TechnischeDokumentation/Freigegebene%20Dokumente/Technische%20Dokumentation/Software-Architektur/Grundlagenwissen/Software-Design/Clean+Architecture.doc?d=we9a5eb042ed3468d9f06a0a1d93d807f&csf=1&web=1&e=OPtIow)

### Versionskontrolle

[Versionskontrolle](https://bcwfom.sharepoint.com/:f:/r/sites/TechnischeDokumentation/Freigegebene%20Dokumente/Entwickleranleitungen/Entwicklungsumgebung/Git?csf=1&web=1&e=tkaTCa)

### Musterlösungen/Entwurfsmuster/Design Patterns

[Entwurfsmuster](https://bcwfom.sharepoint.com/:f:/r/sites/TechnischeDokumentation/Freigegebene%20Dokumente/Technische%20Dokumentation/Software-Architektur/Grundlagenwissen/Software-Design/Entwurfsmuster?csf=1&web=1&e=rFXuF2)

### Unit-Tests

[Unit-Tests](https://bcwfom.sharepoint.com/:f:/r/sites/TechnischeDokumentation/Freigegebene%20Dokumente/Entwickleranleitungen/Testen/Unit-Tests?csf=1&web=1&e=EvFnph)

### Logging

[Logging & Monitoring](https://bcwfom.sharepoint.com/:f:/r/sites/TechnischeDokumentation/Freigegebene%20Dokumente/Entwickleranleitungen/Logging%20%26%20Monitoring?csf=1&web=1&e=ioKoUN)

---

**Version:** 1.0  
**Letzte Aktualisierung:** 26. Februar 2025  
**Maintainer:** IT.SE Architektur-Gilde
