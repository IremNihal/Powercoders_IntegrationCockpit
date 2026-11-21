"""Baut aus den Exporten die Daten für das Mockup (cockpit-mockup.html, Array `R`).

Nutzt die bestehenden Regeln (regeln.ziel1, ziele23.ziel2/ziel3) und das Excel-Einlesen
(schema.py / laden.py) unverändert – es wird nichts neu berechnet, nur umgeformt. Es werden
keine echten Namen erzeugt; die Anzeige-Bezeichnung ist eine neutrale «Klient:in <Nr.>».

Aufruf (gibt JSON auf stdout):  python build_daten.py
"""
from __future__ import annotations

import json
import re

import pandas as pd

from cockpit import daten
from cockpit.laden import ordner_lesen
from cockpit.regeln import ziel1
from cockpit.ziele23 import ziel2, ziel3

# Stand (regeln/ziele23) -> Mockup-Code
STAND2G = {
    "Erreicht": "e", "Erreicht nach Frist": "e", "Auf Kurs": "t",
    "Gefährdet": "r", "Frist verpasst": "x", "Nicht anwendbar": "n",
}


def _iso(ts) -> str:
    return "" if ts is None or pd.isna(ts) else pd.Timestamp(ts).strftime("%Y-%m-%d")


def _int(v, default=0) -> int:
    try:
        if v is None or pd.isna(v):
            return default
        return int(v)
    except (TypeError, ValueError):
        return default


def _str(v, default="") -> str:
    return default if v is None or (not isinstance(v, str) and pd.isna(v)) else str(v)


def _pensum_pro_zemis(d: dict, stichtag: pd.Timestamp) -> dict:
    """Aktuelles Pensum (%) pro Zemis-Nr. aus Erwerb: laufende Stelle bevorzugt, sonst höchstes."""
    ew = d.get("erwerb")
    if ew is None or ew.empty:
        return {}
    e = ew.copy()
    e["pensum"] = pd.to_numeric(e["pensum"], errors="coerce")
    e = e.dropna(subset=["pensum"])
    laufend = e[e["bis"].isna() | (e["bis"] >= stichtag)]
    quelle = laufend if not laufend.empty else e
    return quelle.groupby("zemis")["pensum"].max().to_dict()


def _monate_aus_grund(grund: str) -> int:
    """Liest «seit N Tagen» aus dem Ziel-2-Grundtext (bereits berechnet) und rechnet in Monate um."""
    m = re.search(r"seit\s+(\d+)\s+Tagen", _str(grund))
    return (int(m.group(1)) // 30) if m else 0


def baue(d: dict | None = None, stichtag="2026-11-21") -> list[dict]:
    stichtag = pd.Timestamp(stichtag)
    if d is None:
        d, _ = ordner_lesen(daten.quelle())
    z1 = ziel1(d, stichtag)
    z2 = ziel2(d, stichtag).set_index("zemis")
    z3 = ziel3(d, stichtag).set_index("dossier")
    kl = d["klient"].drop_duplicates("zemis").set_index("zemis")
    pens = _pensum_pro_zemis(d, stichtag)

    out = []
    for i, (_, r) in enumerate(z1.sort_values(["dossier", "klientennr"]).iterrows()):
        z = r["zemis"]
        doss = r["dossier"]
        k = kl.loc[z] if z in kl.index else None
        r2 = z2.loc[z] if z in z2.index else None
        r3 = z3.loc[doss] if doss in z3.index else None

        g1, g2, g3 = r["stand"], (r2["stand"] if r2 is not None else "Nicht anwendbar"), (r3["stand"] if r3 is not None else "Nicht anwendbar")
        dl1 = "" if g1 == "Nicht anwendbar" else _iso(r.get("frist"))
        dl2 = "" if g2 == "Nicht anwendbar" or r2 is None else _iso(r2.get("zust_ende"))
        dl3 = "" if g3 == "Nicht anwendbar" or r3 is None else _iso(r3.get("zust_ende"))

        out.append({
            "id": i,
            "n": f"Klient:in {_str(r.get('klientennr'))}",   # kein echter Name
            "hh": _str(doss),
            "nat": _str(k.get("nationalitaet") if k is not None else ""),
            "mt": _str(k.get("muttersprache") if k is not None else ""),
            "lat": 1 if (k is not None and bool(k.get("alphabetisiert"))) else 0,
            "sy": _int(k.get("schuljahre") if k is not None else 0),
            "age": _int(r.get("alter")),
            "entry": _iso(r.get("einreise")),
            "st": _str(r.get("status")),
            "g": [STAND2G.get(g1, "n"), STAND2G.get(g2, "n"), STAND2G.get(g3, "n")],
            "dl": [dl1, dl2, dl3],
            "course": 1 if bool(r.get("kurs_laufend")) else 0,
            "lang": _str(r.get("grund")),
            "work": _str(r2.get("grund") if r2 is not None else ""),
            "fin": _str(r3.get("grund") if r3 is not None else ""),
            "pens": _int(pens.get(z, 0)),
            "mo": _monate_aus_grund(r2.get("grund") if r2 is not None else ""),
            "free": _int((r3.get("tage_ohne_sh") // 30) if (r3 is not None and pd.notna(r3.get("tage_ohne_sh"))) else 0),
            "cn": _int(r.get("klientennr")),
            "sw": _str(r.get("sozialarbeit"), "–"),   # Fallführung aus dem Klient-Export
        })
    return out


def als_json(d: dict | None = None, stichtag="2026-11-21") -> str:
    return json.dumps(baue(d, stichtag), ensure_ascii=False)


if __name__ == "__main__":
    print(als_json())
