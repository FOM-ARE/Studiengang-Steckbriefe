"""Tests fuer DWH-API Cache."""

import time
from unittest.mock import MagicMock, Mock, patch

import pytest

from studiengang_steckbriefe.services.dwh_api_cache import (
    APIResponseCache,
    cached_api_call,
    get_cache,
    init_cache,
    invalidate_cache,
)


@pytest.fixture
def cache():
    """Erstellt einen Test-Cache mit 1 Sekunde TTL."""
    return APIResponseCache(ttl_seconds=1)


@pytest.fixture
def mock_api_response():
    """Mock-API-Response."""
    return {
        "filter": {"Semester": "2026-WS", "Institut": "FOM"},
        "werte": [{"Gesamtstudierende(mit_UV)": 44525}],
    }


class TestAPIResponseCache:
    """Tests fuer APIResponseCache."""

    def test_cache_init(self, cache):
        """Test: Cache wird korrekt initialisiert."""
        assert cache.ttl_seconds == 1
        assert len(cache._cache) == 0

    def test_cache_set_and_get(self, cache, mock_api_response):
        """Test: Wert setzen und abrufen."""
        cache.set("gesamtstudierende", {"Semester": "2026-WS"}, mock_api_response)

        result = cache.get("gesamtstudierende", {"Semester": "2026-WS"})
        assert result == mock_api_response

    def test_cache_miss(self, cache):
        """Test: Cache-Miss wenn Schluessel nicht existiert."""
        result = cache.get("gesamtstudierende", {"Semester": "2026-WS"})
        assert result is None

    def test_cache_expiration(self, cache, mock_api_response):
        """Test: Eintrag wird nach TTL geloescht."""
        cache.set("gesamtstudierende", {"Semester": "2026-WS"}, mock_api_response)

        # Sofort abrufen - sollte funktionieren
        assert cache.get("gesamtstudierende", {"Semester": "2026-WS"}) is not None

        # 1.1 Sekunden warten
        time.sleep(1.1)

        # Jetzt sollte abgelaufen sein
        assert cache.get("gesamtstudierende", {"Semester": "2026-WS"}) is None

    def test_cache_key_uniqueness(self, cache, mock_api_response):
        """Test: Unterschiedliche Parameter ergeben unterschiedliche Keys."""
        response1 = {"data": "semester_ws"}
        response2 = {"data": "semester_ss"}

        cache.set("gesamtstudierende", {"Semester": "2026-WS"}, response1)
        cache.set("gesamtstudierende", {"Semester": "2026-SS"}, response2)

        assert cache.get("gesamtstudierende", {"Semester": "2026-WS"}) == response1
        assert cache.get("gesamtstudierende", {"Semester": "2026-SS"}) == response2

    def test_cache_clear(self, cache, mock_api_response):
        """Test: Cache.clear() loescht alle Eintraege."""
        cache.set("gesamtstudierende", {"Semester": "2026-WS"}, mock_api_response)
        cache.set("gesamtstudierende", {"Semester": "2026-SS"}, mock_api_response)

        assert len(cache._cache) == 2

        cache.clear()

        assert len(cache._cache) == 0
        assert cache.get("gesamtstudierende", {"Semester": "2026-WS"}) is None

    def test_cache_clear_expired(self, cache, mock_api_response):
        """Test: clear_expired() entfernt nur abgelaufene Eintraege."""
        cache.set("gesamtstudierende", {"Semester": "2026-WS"}, mock_api_response)

        # Warte 1.1 Sekunden
        time.sleep(1.1)

        # Neuer Eintrag (nicht abgelaufen)
        cache.set("gesamtstudierende", {"Semester": "2026-SS"}, mock_api_response)

        # Alte Eintraege loeschen
        removed = cache.clear_expired()

        assert removed == 1
        assert cache.get("gesamtstudierende", {"Semester": "2026-WS"}) is None
        assert cache.get("gesamtstudierende", {"Semester": "2026-SS"}) is not None

    def test_cache_stats(self, cache, mock_api_response):
        """Test: Cache-Statistiken."""
        cache.set("gesamtstudierende", {"Semester": "2026-WS"}, mock_api_response)
        cache.set("gesamtstudierende", {"Semester": "2026-SS"}, mock_api_response)

        stats = cache.stats()

        assert stats["total_entries"] == 2
        assert stats["ttl_seconds"] == 1
        assert stats["cache_size_kb"] > 0

    def test_cache_params_none(self, cache, mock_api_response):
        """Test: Cache mit params=None."""
        cache.set("gesamtstudierende", None, mock_api_response)
        result = cache.get("gesamtstudierende", None)

        assert result == mock_api_response

    def test_cache_params_different_order(self, cache, mock_api_response):
        """Test: Unterschiedliche Reihenfolge der Parameter ergibt gleichen Key."""
        cache.set(
            "gesamtstudierende",
            {"Semester": "2026-WS", "HSZ": "DLS"},
            mock_api_response,
        )

        # Gleiche Parameter, andere Reihenfolge
        result = cache.get("gesamtstudierende", {"HSZ": "DLS", "Semester": "2026-WS"})

        assert result == mock_api_response


class TestGlobalCache:
    """Tests fuer globale Cache-Funktionen."""

    def test_init_cache(self):
        """Test: init_cache() initialisiert globale Instanz."""
        init_cache(ttl_seconds=600)
        cache = get_cache()

        assert cache is not None
        assert cache.ttl_seconds == 600

    def test_get_cache_creates_if_not_exists(self):
        """Test: get_cache() erstellt Cache, wenn nicht vorhanden."""
        # Setze auf None
        import studiengang_steckbriefe.services.dwh_api_cache as cache_module

        cache_module._cache_instance = None

        cache = get_cache()

        assert cache is not None
        assert isinstance(cache, APIResponseCache)

    def test_invalidate_cache(self):
        """Test: invalidate_cache() loescht Cache."""
        init_cache()
        cache = get_cache()

        # Fuege Eintraege hinzu
        cache.set("endpoint", {"param": "value"}, {"data": "test"})
        assert len(cache._cache) == 1

        # Cache invalidieren
        invalidate_cache()

        # Cache sollte leer sein
        assert len(cache._cache) == 0


class TestCachedAPICall:
    """Tests fuer cached_api_call()."""

    def test_cached_api_call_on_hit(self):
        """Test: cached_api_call() gibt gecachten Wert zurueck."""
        init_cache(ttl_seconds=10)
        cache = get_cache()

        # Mock-Connector-Methode
        mock_method = Mock(return_value={"data": "response"})

        # Erstes Call
        result1 = cached_api_call(mock_method, "endpoint", {"param": "value"})
        assert result1 == {"data": "response"}
        assert mock_method.call_count == 1

        # Zweites Call - sollte aus Cache kommen
        result2 = cached_api_call(mock_method, "endpoint", {"param": "value"})
        assert result2 == {"data": "response"}
        assert mock_method.call_count == 1  # Nicht erhoehen!

    def test_cached_api_call_on_miss(self):
        """Test: cached_api_call() macht API-Call bei Cache-Miss."""
        init_cache(ttl_seconds=10)

        mock_method = Mock(return_value={"data": "response1"})

        # Erstes Call mit Parametern
        result1 = cached_api_call(mock_method, "endpoint1", {"param": "value1"})
        # Zweites Call mit unterschiedlichen Parametern
        result2 = cached_api_call(mock_method, "endpoint2", {"param": "value2"})

        # Beide Calls sollten ausgefuehrt werden
        assert mock_method.call_count == 2
        assert result1 == {"data": "response1"}
        assert result2 == {"data": "response1"}

    def test_cached_api_call_with_ttl_override(self):
        """Test: cached_api_call() mit TTL-Override."""
        init_cache(ttl_seconds=100)
        cache = get_cache()

        mock_method = Mock(return_value={"data": "response"})

        # API-Call mit TTL-Override
        cached_api_call(
            mock_method, "endpoint", {"param": "value"}, ttl_override=50
        )

        # In der Praxis wuerde TTL-Override die Instanz-TTL ueberschreiben
        # (Diese Test ist eher eine Platzhalter fuer zukuenftige Erweiterung)
        assert mock_method.call_count == 1

    def test_cached_api_call_no_params(self):
        """Test: cached_api_call() ohne Parameter."""
        init_cache(ttl_seconds=10)

        mock_method = Mock(return_value={"data": "response"})

        result1 = cached_api_call(mock_method, "endpoint", None)
        result2 = cached_api_call(mock_method, "endpoint", None)

        # Zweiter Call sollte aus Cache kommen
        assert mock_method.call_count == 1
        assert result1 == result2


class TestCacheEdgeCases:
    """Tests fuer Edge Cases."""

    def test_cache_with_empty_params(self):
        """Test: Cache mit leeren Parametern."""
        cache = APIResponseCache()
        response = {"data": "test"}

        cache.set("endpoint", {}, response)
        result = cache.get("endpoint", {})

        assert result == response

    def test_cache_large_response(self):
        """Test: Cache mit grosser Response."""
        cache = APIResponseCache()

        # Grosse Response (viele Eintraege)
        large_response = {
            "werte": [{"data": f"row_{i}"} for i in range(1000)]
        }

        cache.set("endpoint", {"param": "value"}, large_response)
        result = cache.get("endpoint", {"param": "value"})

        assert result == large_response
        assert len(result["werte"]) == 1000

    def test_cache_concurrent_set_get(self):
        """Test: Cache-Konsistenz bei schnellen Set/Get Operationen."""
        cache = APIResponseCache(ttl_seconds=10)

        for i in range(100):
            cache.set(f"endpoint_{i}", None, {"data": i})

        for i in range(100):
            result = cache.get(f"endpoint_{i}", None)
            assert result == {"data": i}
