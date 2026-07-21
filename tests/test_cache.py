"""Tests fuer services/cache.py."""

import time

import pytest

from studiengang_steckbriefe.services.cache import (
    cache_clear,
    cache_delete,
    cache_get,
    cache_keys,
    cache_set,
    cache_status,
)


@pytest.fixture(autouse=True)
def clear_before_each():
    """Leert den Cache vor jedem Test."""
    cache_clear()
    yield
    cache_clear()


class TestCacheSetGet:
    def test_set_und_get(self):
        cache_set("key1", {"wert": 42})
        assert cache_get("key1") == {"wert": 42}

    def test_get_nicht_vorhandener_key(self):
        assert cache_get("existiert_nicht") is None

    def test_ueberschreiben(self):
        cache_set("key1", "alt")
        cache_set("key1", "neu")
        assert cache_get("key1") == "neu"

    def test_verschiedene_typen(self):
        cache_set("str", "text")
        cache_set("list", [1, 2, 3])
        cache_set("int", 99)
        assert cache_get("str") == "text"
        assert cache_get("list") == [1, 2, 3]
        assert cache_get("int") == 99


class TestCacheDelete:
    def test_delete_vorhandener_key(self):
        cache_set("x", 1)
        cache_delete("x")
        assert cache_get("x") is None

    def test_delete_nicht_vorhandener_key_kein_fehler(self):
        cache_delete("existiert_nicht")  # Darf keinen Fehler werfen


class TestCacheClear:
    def test_leert_alles(self):
        cache_set("a", 1)
        cache_set("b", 2)
        cache_clear()
        assert cache_get("a") is None
        assert cache_get("b") is None


class TestCacheStatus:
    def test_leer(self):
        status = cache_status()
        assert status["entries"] == 0
        assert status["oldest"] is None
        assert status["newest"] is None

    def test_mit_eintraegen(self):
        cache_set("a", 1)
        time.sleep(0.01)
        cache_set("b", 2)
        status = cache_status()
        assert status["entries"] == 2
        assert status["oldest"] is not None
        assert status["newest"] >= status["oldest"]

    def test_entries_zaehlt_korrekt(self):
        for i in range(5):
            cache_set(f"key{i}", i)
        assert cache_status()["entries"] == 5


class TestCacheKeys:
    def test_leer(self):
        assert cache_keys() == []

    def test_keys_zurueckgeben(self):
        cache_set("alpha", 1)
        cache_set("beta", 2)
        keys = cache_keys()
        assert "alpha" in keys
        assert "beta" in keys
        assert len(keys) == 2
