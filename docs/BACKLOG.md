# BACKLOG.md - Roadmap und offene Aufgaben

## 🎯 Vision

Eine zentrale, wartbare Plattform zur Visualisierung und Analyse von FOM Studiengang-Steckbriefen basierend auf echten Datenbanken.

## ✅ Abgeschlossene Features (v1.0.0)

- [x] HTML-Frontend mit 5 Hochschulbereichen
- [x] 6 Studiengänge mit Mock-Daten
- [x] HSZ-Filter pro Studiengang  
- [x] Intelligente Semester-Erkennung (SS/WS)
- [x] Responsive Tab-Navigation mit 6 Inhalts-Tabs
- [x] Chart.js Visualisierung
- [x] Tabellen mit Semester-Highlighting
- [x] Dokumentation (Installation, Datenstruktur, Entwicklung)

## 🔄 In Progress

- [ ] index.html vollständig in Production kopiert
- [ ] Fom Logo.jpg kopiert
- [ ] Alle Dokumentationen verfügbar

## 🚀 Nächste Features (Priority 1)

### Authentifizierung & Rollen
- [ ] Login-System integrieren
- [ ] Unterschiedliche Benutzertypen (Admin, Dekan, Lehrer)
- [ ] Rollen-basierte Sichtbarkeit

### Echte Datenbank-Integration
- [ ] SQL Server DWH Verbindung
- [ ] Asgard MariaDB Abfragen
- [ ] API-Endpunkte aufsetzen
- [ ] Daten-Caching implementieren

### Erweiterte Filter
- [ ] Multiple Studiengang-Auswahl
- [ ] Jahr-Filter
- [ ] Semester-vergleich (SS vs WS)

## 📊 Mittelfristig (Priority 2)

### Erweiterte Analysen
- [ ] Export zu PDF/Excel
- [ ] Vergleichs-Dashboard (mehrere Programme)
- [ ] Trend-Prognosen
- [ ] Drill-Down Analysen

### Datenvisualisierung
- [ ] Heatmaps für Zeitreihen
- [ ] Sankey-Diagramme für Studentenfluss
- [ ] Geodaten-Karten für HSZ

### Performance
- [ ] Daten-Pagination
- [ ] Lazy-Loading von Charts
- [ ] Lokales Caching mit Service Worker

## 🎨 Längerfristig (Priority 3)

### UI/UX Verbesserungen
- [ ] Dark Mode
- [ ] Mobile App Version
- [ ] Barrierefreiheit (WCAG 2.1)
- [ ] Multi-Language Support (EN)

### Integrationen
- [ ] Slack Bot für Benachrichtigungen
- [ ] Tableau/Power BI Connectors
- [ ] Moodle LMS Integration
- [ ] Asgard Kalender Sync

### Advanced Features
- [ ] Maschinelles Lernen für Prognosen
- [ ] Anomalieerkennung (ungewöhnliche Abweichungen)
- [ ] Automatische Reports
- [ ] Email-Alerts bei Veränderungen

## 🐛 Bekannte Bugs/Tech Debt

- [ ] Logo-Pfad hart-codiert (sollte relativ sein)
- [ ] Mock-Daten in HTML eingebettet (sollte separate Datei)
- [ ] Keine Error-Handling für externe CDN-Ausfälle
- [ ] Tab-Navigation nicht keyboard-accessible
- [ ] Charts nicht responsive bei Fenster-Resize

## 📝 Dokumentation & Wartung

- [ ] API-Dokumentation erstellen
- [ ] Datenbank-Schema dokumentieren
- [ ] Deployment-Guide verfassen
- [ ] Video-Tutorials aufnehmen
- [ ] User-Manual erstellen (Deutsch + English)

## 💰 Ressourcen & Dependencies

### Technisch
- [ ] SSL-Zertifikat für HTTPS
- [ ] CDN für Chart.js Fallback
- [ ] Datenbank-Verbindungspool
- [ ] Caching-Layer (Redis)

### Personal  
- [ ] Frontend-Developer
- [ ] Backend-Developer
- [ ] DBA (Datenbank-Admin)
- [ ] QA/Tester

### Infrastruktur
- [ ] Produktions-Server
- [ ] Staging-Umgebung
- [ ] Monitoring & Logging
- [ ] Backup-System

## 🎁 Zusätzliche Wünsche (Nice to Have)

- [ ] White-label Option für andere Hochschulen
- [ ] Benchmarking gegen andere FOM-HSZ
- [ ] Alumna-Tracking
- [ ] Karriere-Pfade Analyse
- [ ] Feedback-Aggregation von Studierenden

## 📅 Zeitplan (Estimate)

| Priorität | Feature | Aufwand | Timeline |
|-----------|---------|--------|----------|
| P1 | DB-Integration | 4-6 Wochen | Q2 2026 |
| P1 | Auth-System | 2-3 Wochen | Q2 2026 |
| P2 | Export/PDF | 2 Wochen | Q3 2026 |
| P2 | Heatmaps | 2 Wochen | Q3 2026 |
| P3 | Dark Mode | 1 Woche | Q4 2026 |

## 🔗 Verwandte Projekte

- **Asgard Datenbank**: Quelle für Studierenden-Daten
- **DWH (SQL Server)**: Aggregierte Analyse-Daten
- **Hochschul-Website**: Möglicherweise dort eingebettet
- **Moodle**: Für Kurs-Integration

## 📞 Kontakte & Stakeholder

- **Projektleitung**: [TBD]
- **Business Owner**: [TBD]
- **Technical Lead**: [TBD]
- **Dekane**: [Stakeholder für Requirements]

## 🏆 Erfolgskriterien

### v1.0
- [x] Funktional mit Mock-Daten
- [x] Dokumentiert
- [x] Deploybar

### v1.5
- [ ] Mit echten Daten
- [ ] Authentifizierung
- [ ] Performance optimiert

### v2.0
- [ ] Multi-HSZ Dashboard
- [ ] Advanced Analytics
- [ ] Prediction Models

---

**Zuletzt aktualisiert**: 15. April 2026  
**Nächstes Review**: [TBD]  
**Kontakt**: [TBD]
