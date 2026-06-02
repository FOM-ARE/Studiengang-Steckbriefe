"""Main-Blueprint: Liefert die HTML-Seiten aus."""

from flask import Blueprint, render_template

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Hauptseite – Auth wird client-seitig via /api/auth/me geprueft."""
    return render_template("index.html")


@main_bp.route("/login")
def login_page():
    """Login-Seite mit Entra-ID-Button."""
    return render_template("login.html")
