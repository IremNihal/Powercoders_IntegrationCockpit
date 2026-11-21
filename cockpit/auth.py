"""Einfache Anmeldung mit Rollen (Demo).

Für den Betrieb im Netz der Stadt: Anmeldung über das bestehende Login (SSO / Active Directory)
vor der App, die Rolle kommt dann aus der AD-Gruppe. Diese Datei ist nur für den Prototyp.
"""
import hashlib

SALZ = "asd-cockpit-demo"


def _h(pw: str) -> str:
    return hashlib.sha256((SALZ + pw).encode()).hexdigest()


# Benutzer:in -> (Passwort-Hash, Rolle, Anzeigename = Name in «Fallführung»)
BENUTZER = {
    "anna":    (_h("demo"), "Sozialarbeit", "Anna Muster"),
    "david":   (_h("demo"), "Sozialarbeit", "David Roth"),
    "leitung": (_h("demo"), "Leitung", "Leitung ASD"),
    "daten":   (_h("demo"), "Datenverwaltung", "Datenverwaltung"),
}

ROLLEN_TEXT = {
    "Sozialarbeit": "Sieht nur die eigenen Fälle.",
    "Leitung": "Sieht alle Fälle, Totale und Trends.",
    "Datenverwaltung": "Lädt die Exporte, prüft die Datenqualität, erstellt Exporte.",
}


def pruefen(benutzer: str, passwort: str):
    b = BENUTZER.get(benutzer.strip().lower())
    if b and b[0] == _h(passwort):
        return {"benutzer": benutzer.strip().lower(), "rolle": b[1], "name": b[2]}
    return None
