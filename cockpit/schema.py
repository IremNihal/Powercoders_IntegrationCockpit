"""Die 11 Exporte: Dateierkennung und Spalten-Mapping.

Jede Tabelle hat einen internen Namen und ein Mapping
interner Spaltenname -> mögliche deutsche Spaltennamen im Export.
Kleine Abweichungen (Gross/Klein, Leerzeichen, Umlaute, Bindestriche) werden toleriert.
"""
import re

ZEMIS = ["Zemis Nummer", "Klient/-in Zemis-Nr.", "Zemis-Nr."]
KLNR = ["Klientennummer", "Klientennr."]
DOSSIER = ["Dossier-Nr.", "Dossiernummer"]

TABELLEN = {
    "klient": {
        "titel": "Klient",
        "datei": ["klient"],
        "spalten": {
            "klientennr": KLNR, "zemis": ZEMIS, "dossier": DOSSIER,
            "zust_beginn": ["Zuständigkeitsbeginn"],
            "zust_ende": ["Zuständigkeitsende"],
            "uebergang_gemeinde": ["Datum Übergang Gemeindezuständigkeit"],
            "status_aktuell": ["Verfahrensstand (aktuell)", "Verfahrensstand"],
            "unterstuetzung_aktuell": ["Unterstützung (aktuell)"],
            "sozialarbeit": ["Fallführung (Sozialarbeiter:in)", "Fallführung"],
            "geburtsdatum": ["Geburtsdatum"],
            "geschlecht": ["Geschlecht"],
            "nationalitaet": ["Nationalität Land", "Nationalität"],
            "zivilstand": ["Zivilstand"],
            "muttersprache": ["Muttersprache"],
            "ausbildung": ["Höchste abgeschlossene Ausbildung"],
            "schuljahre": ["Schuljahre vor Einreise"],
            "alphabetisiert": ["Lateinisch alphabetisiert"],
            "analphabetismus": ["Art Analphabetismus"],
            "arbeitsjahre": ["Jahre Arbeitserfahrung vor Einreise"],
        },
        "datum": ["zust_beginn", "zust_ende", "uebergang_gemeinde", "geburtsdatum"],
        "pflicht": ["klientennr", "zemis", "zust_ende", "sozialarbeit", "geburtsdatum"],
    },
    "asylgeschaeft": {
        "titel": "Asylgeschäftsdaten",
        "datei": ["asylgesch"],
        "spalten": {
            "zemis": ZEMIS, "klientennr": KLNR,
            "art": ["Asylgeschäftsart"], "datum": ["Ereignisdatum"],
            "erledigung": ["Erledigung"], "erledigungscode": ["Erledigungscode"],
            "erledigungsdatum": ["Erledigungsdatum"],
        },
        "datum": ["datum", "erledigungsdatum"],
        "pflicht": ["zemis", "art", "datum"],
    },
    "verfahren": {
        "titel": "Asylverfahrensstand",
        "datei": ["asylverfahren"],
        "spalten": {
            "zemis": ZEMIS, "klientennr": KLNR, "dossier": DOSSIER,
            "status": ["Verfahrensstand"], "ab": ["Gültig ab"], "bis": ["Gültig bis"],
        },
        "datum": ["ab", "bis"],
        "pflicht": ["zemis", "status", "ab"],
    },
    "sprache": {
        "titel": "Sprachstand",
        "datei": ["sprachstand"],
        "spalten": {
            "zemis": ZEMIS, "klientennr": KLNR, "sprache": ["Sprache"],
            "niveau": ["Sprachniveau"], "art": ["Art", "Art (Nachweis)"],
            "datum": ["Datum Erreichung"], "bemerkungen": ["Bemerkungen"],
        },
        "datum": ["datum"],
        "pflicht": ["zemis", "niveau", "art", "datum"],
    },
    "foerderung": {
        "titel": "Integrationsförderung und Ausbildung",
        "datei": ["integrationsf"],
        "spalten": {
            "zemis": ZEMIS, "klientennr": KLNR, "start": ["Start"], "abschluss": ["Abschluss"],
            "art": ["Art"], "bezeichnung": ["Bezeichnung"], "stunden": ["Stunden pro Woche"],
            "institution": ["Institution Name"], "bemerkungen": ["Bemerkungen"],
        },
        "datum": ["start", "abschluss"],
        "pflicht": ["zemis", "art", "start"],
    },
    "erwerb": {
        "titel": "Erwerb",
        "datei": ["erwerb"],
        "spalten": {
            "zemis": ZEMIS, "klientennr": KLNR, "von": ["Von"], "bis": ["Bis"],
            "arbeitgeber": ["Arbeitgeber Name"], "ort": ["Arbeitgeber Ort"],
            "pensum": ["Pensum %", "Pensum"], "erwerbsstatus": ["Erwerbsstatus"],
            "einkommen": ["Monatseinkommen brutto CHF"], "stundenlohn": ["Stundenlohn"],
            "unregelmaessig": ["Unregelmässiges Einkommen"], "abtretung": ["Abtretung Sozialdienst"],
            "bemerkungen": ["Bemerkungen"],
        },
        "datum": ["von", "bis"],
        "pflicht": ["zemis", "von", "pensum"],
    },
    "zemis_taetigkeit": {
        "titel": "ZEMIS Tätigkeit",
        "datei": ["zemist"],
        "spalten": {
            "zemis": ZEMIS, "klientennr": KLNR, "beginn": ["Arbeitsbeginn"],
            "bis": ["Verpflichtet bis"], "betrieb": ["Betrieb"],
        },
        "datum": ["beginn", "bis"],
        "pflicht": ["zemis", "beginn"],
    },
    "finanz": {
        "titel": "Finanzielle Unterstützung",
        "datei": ["finanziell"],
        "spalten": {
            "dossier": DOSSIER, "art": ["Unterstützung"],
            "von": ["Finanzielle Unterstützung Gültig von", "Gültig von"],
            "bis": ["Finanzielle Unterstützung Gültig bis", "Gültig bis"],
            "grund": ["Hauptgrund Beendigung Unterstützung"],
        },
        "datum": ["von", "bis"],
        "pflicht": ["dossier", "art", "von"],
    },
    "dossierperson": {
        "titel": "Dossierperson",
        "datei": ["dossierperson"],
        "spalten": {
            "dossier": DOSSIER, "klientennr": KLNR, "zemis": ZEMIS,
            "von": ["Dossierperson Von", "Von"], "bis": ["Dossierperson Bis", "Bis"],
            "rolle": ["Rolle"], "beziehung": ["Beziehung"],
        },
        "datum": ["von", "bis"],
        "pflicht": ["dossier", "klientennr"],
    },
    "unterbringung": {
        "titel": "Unterbringung",
        "datei": ["unterbringung"],
        "spalten": {
            "klientennr": KLNR, "von": ["Von"], "bis": ["Bis"],
            "art": ["Unterbringung Art"], "plz_ort": ["PLZ / Ort"],
        },
        "datum": ["von", "bis"],
        "pflicht": ["klientennr"],
    },
    "zielerreichung": {
        "titel": "Integrationszielerreichung",
        "datei": ["integrationsziel"],
        "spalten": {
            "zemis": ZEMIS, "art": ["Art (Ziel)", "Art"], "datum": ["Erreicht am"],
            "partner": ["Partner (Region)"], "kohorte": ["Jahr Grundgesamtheit (Kohorte)"],
            "status_s": ["Ziel mit Status S erreicht"],
        },
        "datum": ["datum"],
        "pflicht": ["zemis", "art", "datum"],
    },
}


def norm(text: str) -> str:
    """'Klient/-in Zemis-Nr.' -> 'klientinzemisnr'"""
    t = str(text).lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        t = t.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", t)


def tabelle_aus_dateiname(name: str):
    n = norm(name)
    # längere Schlüssel zuerst, damit 'integrationsziel' nicht als 'klient' o.ä. erkannt wird
    kandidaten = sorted(
        ((k, key) for key, t in TABELLEN.items() for k in t["datei"]),
        key=lambda x: -len(x[0]),
    )
    for k, key in kandidaten:
        if norm(k) in n:
            return key
    return None
