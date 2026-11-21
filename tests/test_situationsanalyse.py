"""Tests für die Situationsanalyse-Extraktion.  Start: python -m pytest tests  (oder: python tests/test_situationsanalyse.py)"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cockpit import situationsanalyse as sa

BERICHT = """Situationsanalyse Familie – Dossier D12.30001
Zemis-Nr.: 10000123

Familie
Haushalt mit 3 Person(en). Herkunft Syrien, Muttersprache Arabisch.

Sprache
In lateinischer Schrift alphabetisiert. Vor der Einreise wurden 9 Schuljahre besucht.

Arbeit
6 Jahre Berufserfahrung vor der Einreise. Sucht aktuell eine Anstellung.

Potenzial
Wirkt motiviert und zuverlässig.
"""


def test_felder_auslesen():
    f = sa.extrahiere_text(BERICHT)
    assert f["zemis"] == "10000123"
    assert f["alphabetisiert"] == "ja"
    assert f["schuljahre"] == 9
    assert f["berufserfahrung_jahre"] == 6


def test_nicht_alphabetisiert():
    txt = "Zemis-Nr.: 5\n\nSprache\nDie Person ist nicht alphabetisiert; Alpha-Kurs läuft. 0 Schuljahre.\n"
    f = sa.extrahiere_text(txt)
    assert f["alphabetisiert"] == "nein" and f["schuljahre"] == 0


def test_gesundheit_wird_nicht_gelesen():
    txt = (
        "Zemis-Nr.: 77\n\n"
        "Gesundheit\n"
        "Nicht alphabetisiert laut Bericht. 99 Schuljahre. 40 Jahre Berufserfahrung.\n\n"
        "Sprache\n"
        "In lateinischer Schrift alphabetisiert. 8 Schuljahre.\n\n"
        "Arbeit\n3 Jahre Berufserfahrung vor der Einreise.\n"
    )
    f = sa.extrahiere_text(txt)
    # Werte aus dem Gesundheits-Abschnitt dürfen NICHT durchschlagen
    assert f["alphabetisiert"] == "ja"
    assert f["schuljahre"] == 8
    assert f["berufserfahrung_jahre"] == 3


def test_dateien_dedup_und_zuordnung():
    df = sa.extrahiere_dateien([("a.txt", BERICHT), ("leer.txt", "ohne Zemis\nSprache\nalphabetisiert.\n")])
    # Nur Berichte mit Zemis-Nr. zählen
    assert list(df["zemis"]) == ["10000123"]
    assert df.loc[0, "schuljahre"] == 9


def test_als_merkmale_fuegt_spalten_hinzu():
    m = pd.DataFrame({"zemis": ["10000123", "999"], "erfolg": [True, False]})
    sa_df = sa.extrahiere_dateien([("a.txt", BERICHT)])
    m2, namen = sa.als_merkmale(m, sa_df)
    assert namen == sa.MERKMAL_LABELS
    assert m2.loc[0, sa.ALPHA_LABEL] == "ja"
    assert m2.loc[0, sa.SCHULE_LABEL] == "6–9"      # 9 Schuljahre -> Band "6–9"
    assert m2.loc[0, sa.BERUF_LABEL] == "5 und mehr"  # 6 Jahre -> Band "5 und mehr"
    # Person ohne Bericht bleibt leer
    assert pd.isna(m2.loc[1, sa.ALPHA_LABEL])


def test_leer_kein_absturz():
    m = pd.DataFrame({"zemis": ["1"], "erfolg": [True]})
    m2, namen = sa.als_merkmale(m, sa._frame([]))
    assert namen == [] and list(m2.columns) == ["zemis", "erfolg"]


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
    print("Situationsanalyse-Tests bestanden.")
