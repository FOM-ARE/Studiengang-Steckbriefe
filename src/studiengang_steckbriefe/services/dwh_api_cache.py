"""Cache-Layer fuer DWH-API Responses.

Da die DWH-API-Responses sich nur bei jedem Daten-Reload in der DWH aendern
(nicht bei jeder Anfrage), lohnt sich ein lokales Caching erheblich.

Strategie:
1. In-Memory Cache mit TTL (Time-To-Live)
2. Optional: Redis-Integration fuer verteilt Caching
3. Cache-Invalidation durch scheduler (siehe scheduler.py)
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import Any, Callable

logger = logging.getLogger(__name__)


class APIResponseCache:
    """In-Memory Cache fuer DWH-API Responses mit TTL."""

    def __init__(self, ttl_seconds: int = 3600):
        """
        Initialisiert Cache.

        Args:
            ttl_seconds: Time-To-Live in Sekunden (Default: 1 Stunde)
        """
        self.ttl_seconds = ttl_seconds
        self._cache: dict[str, dict[str, Any]] = {}

    def _make_key(self, endpoint: str, params: dict[str, str] | None) -> str:
        """Generiert Cache-Key aus Endpoint und Parametern."""
        param_str = json.dumps(params or {}, sort_keys=True)
        combined = f"{endpoint}:{param_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    def get(self, endpoint: str, params: dict[str, str] | None = None) -> Any | None:
        """
        Ruft gecachten Wert ab, falls vorhanden und nicht abgelaufen.

        Args:
            endpoint: z.B. 'gesamtstudierende'
            params: Query-Parameter

        Returns:
            Gecachter Wert oder None
        """
        key = self._make_key(endpoint, params)
        entry = self._cache.get(key)

        if not entry:
            return None

        # Pruefen, ob abgelaufen
        if time.time() > entry["expires_at"]:
            del self._cache[key]
            logger.debug(f"Cache-Entry abgelaufen: {key}")
            return None

        logger.debug(f"Cache-Hit: {key}")
        return entry["value"]

    def set(self, endpoint: str, params: dict[str, str] | None, value: Any) -> None:
        """
        Speichert Wert im Cache.

        Args:
            endpoint: z.B. 'gesamtstudierende'
            params: Query-Parameter
            value: Zu cachender Wert (z.B. API-Response)
        """
        key = self._make_key(endpoint, params)
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + self.ttl_seconds,
            "created_at": time.time(),
        }
        logger.debug(f"Cache-Set: {key} (TTL: {self.ttl_seconds}s)")

    def clear(self) -> None:
        """Leert den gesamten Cache."""
        self._cache.clear()
        logger.info(f"Cache geleert ({len(self._cache)} Eintraege removed)")

    def clear_expired(self) -> int:
        """
        Entfernt abgelaufene Eintraege.

        Returns:
            Anzahl der geloeschten Eintraege
        """
        now = time.time()
        expired_keys = [k for k, v in self._cache.items() if v["expires_at"] < now]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.debug(f"Cache: {len(expired_keys)} abgelaufene Eintraege geleert")
        return len(expired_keys)

    def stats(self) -> dict[str, Any]:
        """Gibt Cache-Statistiken zurueck."""
        self.clear_expired()
        return {
            "total_entries": len(self._cache),
            "ttl_seconds": self.ttl_seconds,
            "cache_size_kb": len(json.dumps(self._cache)) / 1024,
        }


# Globale Cache-Instanz
_cache_instance: APIResponseCache | None = None


def init_cache(ttl_seconds: int = 3600) -> None:
    """
    Initialisiert die globale Cache-Instanz.

    Sollte bei App-Start aufgerufen werden (siehe web/__init__.py).

    Args:
        ttl_seconds: Cache TTL in Sekunden
    """
    global _cache_instance
    _cache_instance = APIResponseCache(ttl_seconds=ttl_seconds)
    logger.info(f"API-Response-Cache initialisiert (TTL: {ttl_seconds}s)")


def get_cache() -> APIResponseCache:
    """Gibt die globale Cache-Instanz zurueck."""
    if _cache_instance is None:
        init_cache()
    return _cache_instance


def cached_api_call(
    connector_method: Callable[..., Any],
    endpoint: str,
    params: dict[str, str] | None = None,
    ttl_override: int | None = None,
) -> Any:
    """
    Wrapper fuer API-Calls mit automatischem Caching.

    Args:
        connector_method: z.B. connector.get_gesamtstudierende
        endpoint: z.B. 'gesamtstudierende'
        params: Query-Parameter
        ttl_override: Optional TTL-Override fuer diesen Call

    Returns:
        API-Response (aus Cache oder neu abgerufen)
    """
    cache = get_cache()

    # Versuche, aus Cache zu laden
    cached = cache.get(endpoint, params)
    if cached is not None:
        return cached

    # Nicht im Cache - API-Call machen
    logger.debug(f"Cache-Miss: {endpoint} - API-Call starten...")
    result = connector_method(**params) if params else connector_method()

    # In Cache speichern
    cache.set(endpoint, params, result)

    return result


def invalidate_cache() -> None:
    """
    Invalidiert gesamten Cache.

    Sollte nach DWH-Reload aufgerufen werden (siehe scheduler.py).
    """
    cache = get_cache()
    cache.clear()
    logger.info("API-Response-Cache vollstaendig invalidiert (DWH-Reload)")
