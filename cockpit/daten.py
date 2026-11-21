"""Gemeinsamer Datenzugriff für alle Ansichten (mit Cache). Baut auch die lokale Datenbank."""
from pathlib import Path
import streamlit as st

from .laden import ordner_lesen
from .regeln import ziel1, datenqualitaet
from .ziele23 import ziel2, ziel3, ampel_matrix
from . import datenbank

BASIS = Path(__file__).resolve().parent.parent
EXPORT = BASIS / "daten" / "export"
DEMO = BASIS / "daten" / "demo"
DB = BASIS / "daten" / "cockpit.sqlite"


def quelle() -> Path:
    """Echte Exporte, falls vorhanden; sonst Demodaten (werden bei Bedarf erzeugt).

    Die Demodaten sind nicht versioniert (.gitignore), deshalb fehlen sie z. B. auf
    dem Deploy-Server und werden beim ersten Start synthetisch erzeugt.
    """
    if any(EXPORT.glob("*.xlsx")):
        return EXPORT
    if not any(DEMO.glob("*.xlsx")):
        _demo_erzeugen()
    return DEMO


def _demo_erzeugen():
    import sys
    tools = str(BASIS / "tools")
    if tools not in sys.path:
        sys.path.insert(0, tools)
    from synthetische_daten import erzeugen
    with st.spinner("Demodaten werden erzeugt …"):
        erzeugen(400, DEMO)


def ist_demo() -> bool:
    return quelle() == DEMO


def _stempel(ordner: Path):
    return tuple(sorted((f.name, f.stat().st_mtime) for f in ordner.glob("*.xlsx")))


@st.cache_data(show_spinner="Exporte werden gelesen …")
def _laden(ordner: str, stempel):
    return ordner_lesen(Path(ordner))


@st.cache_data(show_spinner="Ziele werden berechnet …")
def _rechnen(ordner: str, stempel, stichtag):
    d, _ = _laden(ordner, stempel)
    z1 = ziel1(d, stichtag)
    z2 = ziel2(d, stichtag)
    z2["einreisejahr"] = z2["einreise"].dt.year.astype("Int64")
    z3 = ziel3(d, stichtag)
    m = ampel_matrix(z1, z2, z3)
    dq = datenqualitaet(d, z1, stichtag)
    db = datenbank.bauen(DB, d, {"ergebnis_ziel1": z1, "ergebnis_ziel2": z2, "ergebnis_ziel3": z3, "ergebnis_ampel": m})
    return {"z1": z1, "z2": z2, "z3": z3, "matrix": m, "dq": dq, "db": db}


def alles(stichtag):
    q = quelle()
    s = _stempel(q)
    d, berichte = _laden(str(q), s)
    r = _rechnen(str(q), s, stichtag)
    return d, berichte, r
