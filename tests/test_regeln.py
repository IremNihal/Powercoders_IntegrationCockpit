"""Kleine Tests für die Ziel-1-Regeln.  Start: python -m pytest tests  (oder: python tests/test_regeln.py)"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from cockpit.schema import TABELLEN
from cockpit.regeln import ziel1

T = pd.Timestamp
STICHTAG = T("2026-11-20")


def leer():
    return {k: pd.DataFrame(columns=list(s["spalten"]), dtype=object) for k, s in TABELLEN.items()}


def person(d, z, status, geb, einreise, sa="Test SA", alpha=None):
    d["klient"].loc[len(d["klient"])] = {"klientennr": "k" + z, "zemis": z, "dossier": "D1", "zust_beginn": T(einreise),
                                         "zust_ende": T("2031-01-01"), "uebergang_gemeinde": pd.NaT,
                                         "status_aktuell": status, "sozialarbeit": sa, "geburtsdatum": T(geb),
                                         "alphabetisiert": alpha}
    d["asylgeschaeft"].loc[len(d["asylgeschaeft"])] = {"zemis": z, "art": "Aufenthalt (Einreise)", "datum": T(einreise)}


def sprache(d, z, niveau, art, datum, bem=None):
    d["sprache"].loc[len(d["sprache"])] = {"zemis": z, "sprache": "Deutsch", "niveau": niveau, "art": art,
                                           "datum": T(datum), "bemerkungen": bem}


def fertig(d):
    for k, s in TABELLEN.items():
        for c in s["datum"]:
            d[k][c] = pd.to_datetime(d[k][c])
        for c in ("zemis", "klientennr", "dossier"):
            if c in d[k]:
                d[k][c] = d[k][c].astype("string")
    return d


def stand(z1, z):
    return z1.set_index("zemis").loc[z, "stand"]


def test_regeln():
    d = leer()
    person(d, "1", "B-FL", "1990-01-01", "2024-01-10"); sprache(d, "1", "A1", "Zertifikat", "2025-05-01", "telc A1")
    person(d, "2", "VA", "1990-01-01", "2024-01-10"); sprache(d, "2", "A1", "Zertifikat", "2025-05-01", None)
    person(d, "3", "S", "1990-01-01", "2024-01-10")
    person(d, "4", "VA", "2012-01-01", "2024-01-10")              # 14 Jahre -> nicht anwendbar
    person(d, "5", "F-FL", "1990-01-01", "2023-01-10")             # Frist 10.01.2026 vorbei
    person(d, "6", "B-FL", "2009-06-01", "2022-01-10")             # wird 2025 16 -> Frist 01.06.2028
    person(d, "7", "VA", "1990-01-01", "2024-01-10"); sprache(d, "7", "A1", "Muttersprache", "2024-01-10")
    person(d, "8", "VA", "1990-01-01", "2020-01-10"); sprache(d, "8", "A1", "Zertifikat", "2023-06-01", "fide")  # nach Frist
    z1 = ziel1(fertig(d), STICHTAG)
    assert stand(z1, "1") == "Erreicht"
    assert stand(z1, "2") != "Erreicht", "Zertifikat ohne telc/fide zählt nicht"
    assert stand(z1, "3") == "Nicht anwendbar"
    assert stand(z1, "4") == "Nicht anwendbar"
    assert stand(z1, "5") == "Frist verpasst"
    assert z1.set_index("zemis").loc["6", "frist"] == T("2028-06-01")
    assert stand(z1, "7") == "Erreicht"
    assert stand(z1, "8") == "Erreicht nach Frist"
    print("Alle Regel-Tests bestanden.")


def test_ziel2_ziel3():
    from cockpit.ziele23 import ziel2, ziel3
    d = leer()
    for z in ("a", "b", "c", "e"):
        person(d, z, "B-FL", "1990-01-01", "2023-01-10")
    person(d, "f", "VA", "2006-01-01", "2023-01-10")
    def job(z, von, bis, pensum):
        d["erwerb"].loc[len(d["erwerb"])] = {"zemis": z, "von": T(von), "bis": T(bis) if bis else pd.NaT, "pensum": pensum}
    job("a", "2025-01-01", "2025-08-15", 60)                                   # 7 Monate -> erreicht
    job("b", "2026-01-01", None, 50)                                           # 50 % -> nicht
    job("c", "2025-01-01", "2025-04-30", 100); job("c", "2025-05-10", "2025-08-30", 100)  # Unterbruch -> nicht
    job("e", "2025-01-01", "2025-04-30", 80); job("e", "2025-05-01", "2025-09-30", 80)    # ohne Unterbruch -> erreicht
    d["foerderung"].loc[0] = {"zemis": "f", "start": T("2025-08-01"), "abschluss": pd.NaT, "art": "Sek II"}
    z2 = ziel2(fertig(d), STICHTAG).set_index("zemis")["stand"]
    assert z2["a"] == "Erreicht" and z2["e"] == "Erreicht" and z2["f"] == "Erreicht"
    assert z2["b"] != "Erreicht" and z2["c"] != "Erreicht", z2.to_dict()

    d = leer()
    def hh(dossier, z, ende):
        person(d, z, "B-FL", "1990-01-01", "2022-01-10")
        d["klient"].loc[d["klient"]["zemis"] == z, "dossier"] = dossier
        d["klient"].loc[d["klient"]["zemis"] == z, "zust_ende"] = T(ende)
    hh("D-A", "1", "2028-01-01"); hh("D-B", "2", "2028-01-01"); hh("D-C", "3", "2027-04-01")
    def fu(dossier, art, von, bis):
        d["finanz"].loc[len(d["finanz"])] = {"dossier": dossier, "art": art, "von": T(von), "bis": T(bis) if bis else pd.NaT}
    fu("D-A", "Sozialhilfe", "2022-01-10", "2025-01-01")                       # seit 2025 frei -> erreicht
    fu("D-B", "Sozialhilfe", "2022-01-10", "2025-01-01"); fu("D-B", "Sozialhilfe", "2025-07-01", None)  # Rückfall
    fu("D-C", "Sozialhilfe", "2022-01-10", None)                               # nur noch 4 Mt. -> verpasst
    z3 = ziel3(fertig(d), STICHTAG).set_index("dossier")["stand"]
    assert z3["D-A"] == "Erreicht" and z3["D-B"] != "Erreicht" and z3["D-C"] == "Frist verpasst", z3.to_dict()
    print("Ziel-2/3-Tests bestanden.")


if __name__ == "__main__":
    test_regeln()
    test_ziel2_ziel3()
