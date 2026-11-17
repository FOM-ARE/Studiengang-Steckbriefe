# DWH-API Quick Start

## 🚀 5-Minuten Quickstart

### 1. Abhängigkeiten prüfen
```bash
# requests ist bereits in requirements installiert (pyproject.toml)
pip list | grep requests
# azure-identity für Key Vault (bereits vorhanden)
pip list | grep azure
```

### 2. API-Key Setup (einmalig)
```bash
# Azure CLI - API-Key anzeigen (nur für Administratoren)
az keyvault secret show --name "DWH-API" --vault-name "your-vault"

# Verifikation: Von lokalem Test-Script
python -c "
from studiengang_steckbriefe.services.dwh_api_connector import DWHAPIConnector
connector = DWHAPIConnector(api_key='dwh_IQiGzbf4vqxnm4iwnOdJrzn7WDfVRk_RvpFaAYv9gNM')
response = connector.get_gesamtstudierende(semester='2026-WS')
print('✅ API funktioniert!')
print(response)
"
```

### 3. Einfacher API-Call in deiner App

```python
# In web/__init__.py oder steckbrief.py
from studiengang_steckbriefe.services.dwh_api_connector import create_connector_from_flask_config
from studiengang_steckbriefe.services.dwh_api_cache import init_cache, cached_api_call

# Bei App-Initialisierung
def create_app(config_name="default"):
    app = Flask(__name__)
    # ... app config ...
    
    # DWH-API Cache initialisieren
    init_cache(ttl_seconds=3600)
    
    return app

# In einem Endpoint/Service
def get_studierende_daten():
    # Connector mit Flask-Config erstellen
    connector = create_connector_from_flask_config(current_app)
    
    # API-Call mit Caching
    response = cached_api_call(
        connector.get_gesamtstudierende,
        "gesamtstudierende",
        {
            "semester": "2026-WS",
            "gruppierung": "Hochschulzentrum"
        }
    )
    
    return response["werte"]
```

### 4. Daten verarbeiten

```python
# API Response-Format
{
    "filter": {
        "Semester": "2026-WS",
        "Ausrichtung": "Nationale Studienprogramme",
        "Institut": "FOM"
    },
    "gruppierung": ["Hochschulzentrum"],
    "werte": [
        {
            "gruppen": "@{Hochschulzentrum=DLS}",
            "Gesamtstudierende(mit_UV)": 15234,
            "Gesamtstudierende(ohne_UV)": 15000
        },
        {
            "gruppen": "@{Hochschulzentrum=Berlin}",
            "Gesamtstudierende(mit_UV)": 8900,
            "Gesamtstudierende(ohne_UV)": 8700
        }
    ]
}

# Verarbeitung
for row in response["werte"]:
    print(f"HSZ: {row['gruppen']}, Studierende: {row['Gesamtstudierende(mit_UV)']}")
```

## 📌 Häufige Use Cases

### Use Case 1: Gesamtstudierende pro Semester (Zeitreihe)
```python
connector = create_connector_from_flask_config(current_app)

# 7 letzte Semester abrufen
response = connector.get_gesamtstudierende(
    semester="2026-WS;2026-SS;2025-WS;2025-SS;2024-WS;2024-SS;2023-WS",
    gruppierung="Semester"
)

# Verarbeitung
for row in response["werte"]:
    semester = row["gruppen"].split("=")[1].rstrip("}")
    gesamtstudierende = row["Gesamtstudierende(mit_UV)"]
    print(f"{semester}: {gesamtstudierende}")
```

### Use Case 2: Studierende pro Hochschulzentrum
```python
connector = create_connector_from_flask_config(current_app)

response = connector.get_gesamtstudierende(
    semester="2026-WS",
    gruppierung="Hochschulzentrum"
)

# Ergebnis: Array mit HSZ-Aufschlüsselung
```

### Use Case 3: Studierende pro Studiengang
```python
connector = create_connector_from_flask_config(current_app)

response = connector.get_gesamtstudierende(
    semester="2026-WS",
    gruppierung="Studiengang"
)

# Ergebnis: Array mit Studiengang-Aufschlüsselung
```

### Use Case 4: Mehrere Dimensionen kombinieren
```python
connector = create_connector_from_flask_config(current_app)

response = connector.get_gesamtstudierende(
    semester="2026-WS",
    hochschulzentrum="DLS",
    gruppierung="Studiengang;Zeitmodell"
)

# Ergebnis: Matrix mit Studiengang × Zeitmodell
```

### Use Case 5: Verfügbare Dimensionswerte auflisten
```python
connector = create_connector_from_flask_config(current_app)

# Alle Semester auflisten
semesters = connector.get_dimension_werte("Semester")
# {"dimension": "Semester", "werte": ["2026-WS", "2026-SS", ...]}

# Alle Studiengänge auflisten
studiengaenge = connector.get_dimension_werte("Studiengang")
# {"dimension": "Studiengang", "werte": ["Business Administration (BBA)", ...]}

# Alle HSZ auflisten
hsz = connector.get_dimension_werte("Hochschulzentrum")
# {"dimension": "Hochschulzentrum", "werte": ["DLS", "Berlin", ...]}
```

## 🧪 Unit Tests ausführen

```bash
# Alle API-Tests
pytest tests/test_dwh_api_connector.py -v

# Cache-Tests
pytest tests/test_dwh_api_cache.py -v

# Kombiniert mit Coverage
pytest tests/test_dwh_api_*.py --cov=src/studiengang_steckbriefe/services/dwh_api_* -v
```

## ⚠️ Fehlerbehandlung

```python
from studiengang_steckbriefe.services.dwh_api_connector import DWHAPIConnector
import requests

try:
    connector = create_connector_from_flask_config(current_app)
    response = connector.get_gesamtstudierende(semester="2026-WS")
    
except requests.exceptions.Timeout:
    # API antwortet nicht in Zeit
    current_app.logger.error("DWH-API Timeout - fallback auf Cache/SQL")
    # Fallback implementieren
    
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 401:
        # API-Key ungueltig
        current_app.logger.error("DWH-API: Authentifizierung fehlgeschlagen")
    elif e.response.status_code == 300:
        # Wartungsfenster
        current_app.logger.warning("DWH-API im Wartungsfenster - Anfrage wiederholen")
    elif e.response.status_code == 400:
        # Ungueltige Parameter
        current_app.logger.error(f"DWH-API: Ungueltige Anfrage - {e.response.text}")
    raise
    
except ValueError as e:
    # Ungueltige JSON-Response
    current_app.logger.error(f"DWH-API: Ungueltige Response - {e}")
    raise
```

## 🔍 Debugging

### Cache-Statistiken anzeigen
```python
from studiengang_steckbriefe.services.dwh_api_cache import get_cache

cache = get_cache()
stats = cache.stats()
print(f"Cache-Einträge: {stats['total_entries']}")
print(f"Cache-Größe: {stats['cache_size_kb']} KB")
print(f"TTL: {stats['ttl_seconds']} s")
```

### Logs prüfen
```bash
# Flask Logger beobachten
# In console sollte erscheinen:
# - "DWH-API: Authentifizierungs-Key aus Key Vault geladen"
# - "API-Response-Cache initialisiert"
# - "Cache-Hit: ..."
# - "Cache-Miss: ... - API-Call starten..."
```

### API direkt testen
```bash
# CURL testen
curl -H "X-API-Key: dwh_IQiGzbf4vqxnm4iwnOdJrzn7WDfVRk_RvpFaAYv9gNM" \
  "https://datawarehouseapi.srvs.bcw-intern.local/api/v1/gesamtstudierende?Semester=2026-WS&gruppierung=Semester"
```

## 📖 Weitere Ressourcen

- [Vollständige API-Dokumentation](../docs/DWH_API_INTEGRATION.md)
- [dwh_api_connector.py Source](../src/studiengang_steckbriefe/services/dwh_api_connector.py)
- [dwh_api_cache.py Source](../src/studiengang_steckbriefe/services/dwh_api_cache.py)
- [API Swagger UI](https://datawarehouseapi.srvs.bcw-intern.local/docs/index.html)

## ✅ Checkliste vor Production-Deployment

- [ ] API-Key erfolgreich aus Azure Key Vault geladen
- [ ] `test_dwh_api_connector.py` - alle 18 Tests bestanden
- [ ] `test_dwh_api_cache.py` - alle 20 Tests bestanden
- [ ] Manueller API-Test erfolgreich (siehe "API direkt testen")
- [ ] Cache-Mechanismus funktioniert (siehe "Cache-Statistiken anzeigen")
- [ ] Fallback-Plan implementiert
- [ ] Monitoring konfiguriert
- [ ] Team Training durchgeführt
