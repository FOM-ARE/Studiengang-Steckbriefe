"""Main-Blueprint: Liefert die HTML-Seiten aus."""

from flask import Blueprint, redirect, render_template, session, url_for

main_bp = Blueprint("main", __name__)


@main_bp.route("/", methods=["GET"])
def index():
    """Hauptseite – nur fuer authentifizierte Benutzer."""
    if not session.get("user"):
        return redirect(url_for("main.login_page"))
    return render_template("index.html")


@main_bp.route("/login", methods=["GET"])
def login_page():
    """Login-Seite mit Entra-ID-Button."""
    return render_template("login.html")
