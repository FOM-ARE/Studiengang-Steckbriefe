"""Test-Fixtures fuer die Studiengang-Steckbriefe App."""

import pytest

from studiengang_steckbriefe.web import create_app


@pytest.fixture
def app():
    """Erstellt eine App-Instanz im Testing-Modus."""
    app = create_app("testing")
    yield app


@pytest.fixture
def client(app):
    """Erstellt einen Test-Client."""
    return app.test_client()


@pytest.fixture
def authenticated_client(client):
    """Test-Client mit simulierter Authentifizierung."""
    with client.session_transaction() as sess:
        sess["user"] = {
            "username": "test.user",
            "display_name": "Test User",
            "email": "test.user@fom.de",
            "role": "admin",
        }
    return client
