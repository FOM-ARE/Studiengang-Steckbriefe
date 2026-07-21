"""Tests fuer web/users.py."""
from unittest.mock import patch

_MDB = "studiengang_steckbriefe.web.users.mariadb_connector"


class TestGetUsers:
    def test_erfordert_admin(self, client):
        assert client.get("/api/users").status_code == 401

    def test_gibt_user_liste_zurueck(self, authenticated_client):
        mock_rows = [
            {
                "Id": 1,
                "Berechtigt": "max.mustermann",
                "Recht": "read",
                "Typ": "user",
                "DisplayName": "Max",
                "Aktiv": 1,
            }
        ]
        with patch(f"{_MDB}.query", return_value=mock_rows):
            response = authenticated_client.get("/api/users")
        assert response.status_code == 200
        assert len(response.get_json()["users"]) == 1


class TestAddUser:
    def test_leerer_name_gibt_400(self, authenticated_client):
        response = authenticated_client.post(
            "/api/users", json={"username": "", "typ": "user"}
        )
        assert response.status_code == 400

    def test_ungültiger_typ_gibt_400(self, authenticated_client):
        response = authenticated_client.post(
            "/api/users", json={"username": "max", "typ": "invalid"}
        )
        assert response.status_code == 400

    def test_duplikat_gibt_409(self, authenticated_client):
        with patch(f"{_MDB}.query", return_value=[{"Id": 1}]):
            response = authenticated_client.post(
                "/api/users", json={"username": "max", "typ": "user"}
            )
        assert response.status_code == 409

    def test_neuer_user_erstellt(self, authenticated_client):
        with patch(f"{_MDB}.query", return_value=[]), patch(
            f"{_MDB}.execute", return_value=1
        ):
            response = authenticated_client.post(
                "/api/users", json={"username": "new.user", "typ": "user"}
            )
        assert response.status_code == 201
        assert response.get_json()["ok"] is True


class TestUpdateUser:
    def test_ungültiges_recht_gibt_400(self, authenticated_client):
        response = authenticated_client.put("/api/users/1", json={"recht": "superadmin"})
        assert response.status_code == 400

    def test_nicht_gefunden_gibt_404(self, authenticated_client):
        with patch(f"{_MDB}.execute", return_value=0):
            response = authenticated_client.put("/api/users/99", json={"recht": "admin"})
        assert response.status_code == 404

    def test_recht_aktualisiert(self, authenticated_client):
        with patch(f"{_MDB}.execute", return_value=1):
            response = authenticated_client.put("/api/users/1", json={"recht": "write"})
        assert response.status_code == 200
        assert response.get_json()["ok"] is True


class TestDeleteUser:
    def test_nicht_gefunden_gibt_404(self, authenticated_client):
        with patch(f"{_MDB}.query", return_value=[]), patch(
            f"{_MDB}.execute", return_value=0
        ):
            response = authenticated_client.delete("/api/users/99")
        assert response.status_code == 404

    def test_selbstloeschung_verboten(self, authenticated_client):
        with patch(f"{_MDB}.query", return_value=[{"Berechtigt": "test.user"}]):
            response = authenticated_client.delete("/api/users/1")
        assert response.status_code == 400

    def test_user_deaktiviert(self, authenticated_client):
        with patch(f"{_MDB}.query", return_value=[{"Berechtigt": "anderer.user"}]), patch(
            f"{_MDB}.execute", return_value=1
        ):
            response = authenticated_client.delete("/api/users/2")
        assert response.status_code == 200
        assert response.get_json()["ok"] is True
