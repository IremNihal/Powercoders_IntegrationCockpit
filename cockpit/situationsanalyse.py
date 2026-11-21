"""Situationsanalyse-Extraktion: aus Freitext-Berichten prüfbare Merkmale lesen.

Rein regelbasiert (Regex / Schlüsselwörter), lokal, ohne Netz. Gelesen werden nur:
Alphabetisierung (ja/nein), Schuljahre, Berufserfahrung in Jahren – zugeordnet über die
Zemis-Nr. im Kopf des Berichts. Abschnitte zu Gesundheit/Health werden vor der Auswertung
entfernt und gar nicht erst gelesen. Keine Streamlit-Abhängigkeit, damit testbar.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

# Bekannte Abschnittsüberschriften der Berichte. Gesundheit/Health werden bewusst ausgeschlossen.
ABSCHNITTE = {"familie", "wohnen", "sprache", "arbeit", "potenzial"}
GESPERRT = {"gesundheit", "health", "medizinisch", "psyche", "psychisch"}

FELDER = ["alphabetisiert", "schuljahre", "berufserfahrung_jahre"]

_ZEMIS = re.compile(r"zemis\s*-?\s*nr\.?\s*:?\s*(\d{3,})", re.IGNORECASE)
_SCHULJAHRE = re.compile(r"(\d{1,2})\s*schuljahre?", re.IGNORECASE)
_BERUF = re.compile(r"(\d{1,2})\s*jahre?\s+berufserfahrung", re.IGNORECASE)
_NICHT_ALPHA = re.compile(r"(nicht\s+alphabetisiert|analphabet)", re.IGNORECASE)
_ALPHA = re.compile(r"alphabetisiert", re.IGNORECASE)


def ohne_gesundheit(text: str) -> str:
    """Entfernt Abschnitte mit gesperrter Überschrift (z.B. Gesundheit) komplett.

    Eine Überschrift ist eine kurze Zeile, die nur aus einem bekannten Abschnittstitel
    besteht. Alles ab einer gesperrten Überschrift bis zur nächsten Überschrift (oder
    Textende) wird weggelassen.
    """
    zeilen = text.splitlines()
    out, sperren = [], False
    for zeile in zeilen:
        kopf = zeile.strip().rstrip(":").lower()
        ist_ueberschrift = kopf in ABSCHNITTE or kopf in GESPERRT
        if ist_ueberschrift:
            sperren = kopf in GESPERRT
        if not sperren:
            out.append(zeile)
    return "\n".join(out)


def _zahl(muster: re.Pattern, text: str) -> int | None:
    m = muster.search(text)
    return int(m.group(1)) if m else None


def extrahiere_text(text: str) -> dict:
    """Ein Bericht -> {zemis, alphabetisiert, schuljahre, berufserfahrung_jahre}."""
    sicher = ohne_gesundheit(text)
    zemis = _ZEMIS.search(sicher)
    if _NICHT_ALPHA.search(sicher):
        alpha = "nein"
    elif _ALPHA.search(sicher):
        alpha = "ja"
    else:
        alpha = None
    return {
        "zemis": zemis.group(1) if zemis else None,
        "alphabetisiert": alpha,
        "schuljahre": _zahl(_SCHULJAHRE, sicher),
        "berufserfahrung_jahre": _zahl(_BERUF, sicher),
    }


def _frame(zeilen: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(zeilen, columns=["zemis", "datei", *FELDER])
    if not df.empty:
        df["zemis"] = df["zemis"].astype("string")
        df = df.dropna(subset=["zemis"]).drop_duplicates("zemis", keep="last").reset_index(drop=True)
    return df


def extrahiere_dateien(dateien: list[tuple[str, str]]) -> pd.DataFrame:
    """Liste von (Dateiname, Textinhalt) -> DataFrame, eine Zeile je erkannter Zemis-Nr."""
    zeilen = []
    for name, text in dateien:
        feld = extrahiere_text(text)
        feld["datei"] = name
        zeilen.append(feld)
    return _frame(zeilen)


def extrahiere_ordner(pfad: str | Path) -> pd.DataFrame:
    """Alle *.txt in einem Ordner einlesen und extrahieren."""
    pfad = Path(pfad)
    if not pfad.exists():
        return _frame([])
    dateien = [(p.name, p.read_text(encoding="utf-8")) for p in sorted(pfad.glob("*.txt"))]
    return extrahiere_dateien(dateien)


# ---- Einspeisung in die Stufe-2-Analyse (analysen.merkmale) ----

ALPHA_LABEL = "Alphabetisiert (Situationsanalyse)"
SCHULE_LABEL = "Schuljahre (Situationsanalyse)"
BERUF_LABEL = "Berufserfahrung (Situationsanalyse)"
MERKMAL_LABELS = [ALPHA_LABEL, SCHULE_LABEL, BERUF_LABEL]


def _band(werte: pd.Series, grenzen: list, labels: list) -> pd.Series:
    s = pd.to_numeric(werte, errors="coerce")
    return pd.cut(s, bins=grenzen, labels=labels, right=False).astype("string")


def als_merkmale(m: pd.DataFrame, sa: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Fügt die extrahierten Felder als zusätzliche Merkmal-Spalten zu m (keyed auf 'zemis') hinzu.

    Gibt (erweitertes m, Liste der neuen Merkmalnamen) zurück. Rührt m nicht an, wenn sa leer ist.
    """
    m = m.copy()
    if sa is None or sa.empty:
        return m, []
    idx = sa.set_index("zemis")
    z = m["zemis"].astype("string")
    m[ALPHA_LABEL] = z.map(idx["alphabetisiert"]).astype("string")
    m[SCHULE_LABEL] = _band(z.map(idx["schuljahre"]), [0, 6, 10, 99], ["0–5", "6–9", "10 und mehr"]).values
    m[BERUF_LABEL] = _band(z.map(idx["berufserfahrung_jahre"]), [0, 1, 5, 99], ["keine", "1–4 Jahre", "5 und mehr"]).values
    return m, MERKMAL_LABELS
