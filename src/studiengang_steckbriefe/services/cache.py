"""Cache-Service: In-Memory-Cache mit Timestamps."""

import time

_CACHE: dict[str, dict] = {}


def cache_get(key: str):
    """Gibt gecachten Wert zurueck oder None wenn nicht vorhanden."""
    entry = _CACHE.get(key)
    if entry:
        return entry["data"]
    return None


def cache_set(key: str, data):
    """Speichert Daten im Cache mit Timestamp."""
    _CACHE[key] = {"data": data, "timestamp": time.time()}


def cache_clear():
    """Leert den gesamten Cache."""
    _CACHE.clear()


def cache_delete(key: str):
    """Loescht einen einzelnen Cache-Eintrag."""
    _CACHE.pop(key, None)


def cache_status() -> dict:
    """Gibt den aeltesten und neuesten Cache-Timestamp zurueck."""
    if not _CACHE:
        return {"entries": 0, "oldest": None, "newest": None}
    timestamps = [entry["timestamp"] for entry in _CACHE.values()]
    return {
        "entries": len(_CACHE),
        "oldest": min(timestamps),
        "newest": max(timestamps),
    }


def cache_keys() -> list[str]:
    """Gibt alle Cache-Keys zurueck."""
    return list(_CACHE.keys())
