"""Lokale Datenbank (SQLite, eine Datei, kein Server).

Bildet das Datenmodell des ASD ab: Klient ist die Drehscheibe, Personentabellen hängen über
Zemis-Nr. / Klientennummer daran, Haushaltstabellen über die Dossier-Nr.
Neben den 11 Rohtabellen speichert sie die berechneten Ergebnisse (Ziel 1–3, Ampel),
damit man sie auch mit anderen Werkzeugen (z.B. Excel, Power BI im Netz der Stadt) abfragen kann.
"""
import sqlite3
from pathlib import Path
import pandas as pd

from .schema import TABELLEN

# Verknüpfungen laut Datenmodell: (Tabelle, Spalte) -> (Zieltabelle, Zielspalte)
BEZIEHUNGEN = [
    ("asylgeschaeft", "zemis", "klient", "zemis"),
    ("verfahren", "zemis", "klient", "zemis"),
    ("sprache", "zemis", "klient", "zemis"),
    ("foerderung", "zemis", "klient", "zemis"),
    ("erwerb", "zemis", "klient", "zemis"),
    ("zemis_taetigkeit", "zemis", "klient", "zemis"),
    ("zielerreichung", "zemis", "klient", "zemis"),
    ("unterbringung", "klientennr", "klient", "klientennr"),
    ("dossierperson", "klientennr", "klient", "klientennr"),
    ("finanz", "dossier", "dossierperson", "dossier"),
]
SQL_TYP = {"datum": "DATE"}


def _ddl(key: str) -> str:
    spec = TABELLEN[key]
    spalten = []
    for c in spec["spalten"]:
        typ = "DATE" if c in spec["datum"] else "TEXT"
        spalten.append(f'"{c}" {typ}')
    if key == "klient":
        spalten[0] = '"klientennr" TEXT PRIMARY KEY'
    fks = [f'FOREIGN KEY ("{c}") REFERENCES "{t}"("{tc}")' for (q, c, t, tc) in BEZIEHUNGEN if q == key and t == "klient"]
    return f'CREATE TABLE "{key}" (\n  ' + ",\n  ".join(spalten + fks) + "\n);"


def _fuer_sql(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    for c in out.columns:
        if pd.api.types.is_datetime64_any_dtype(out[c]):
            out[c] = out[c].dt.strftime("%Y-%m-%d")
        else:
            out[c] = out[c].astype(object).where(out[c].notna(), None)
            out[c] = out[c].map(lambda v: v if v is None or isinstance(v, (int, float, str)) else str(v))
    return out


def bauen(pfad: Path, d: dict, ergebnisse: dict) -> dict:
    """Schreibt Rohdaten und Ergebnisse neu in die Datenbank. Gibt den Prüfbericht zurück."""
    pfad = Path(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    tmp = pfad.with_suffix(".tmp")
    tmp.unlink(missing_ok=True)
    con = sqlite3.connect(tmp)
    try:
        klient = d["klient"].drop_duplicates("klientennr")
        for key in TABELLEN:
            con.execute(_ddl(key))
            df = klient if key == "klient" else d[key]
            df = df[list(TABELLEN[key]["spalten"])]
            _fuer_sql(df).to_sql(key, con, if_exists="append", index=False)
        for name, df in ergebnisse.items():
            _fuer_sql(df).to_sql(name, con, if_exists="replace", index=False)
        con.execute('CREATE INDEX ix_klient_zemis ON klient(zemis)')
        con.execute('CREATE INDEX ix_klient_dossier ON klient(dossier)')
        con.commit()
        bericht = pruefen(con, d)
    finally:
        con.close()
    tmp.replace(pfad)
    return bericht


def pruefen(con, d) -> dict:
    """Schlüsselprüfung: Zeilen, deren Schlüssel nicht im Ziel vorkommt (verwaiste Zeilen)."""
    zeilen = []
    for (q, c, t, tc) in BEZIEHUNGEN:
        n = con.execute(f'SELECT COUNT(*) FROM "{q}"').fetchone()[0]
        waise = con.execute(
            f'SELECT COUNT(*) FROM "{q}" WHERE "{c}" IS NOT NULL AND "{c}" NOT IN (SELECT "{tc}" FROM "{t}" WHERE "{tc}" IS NOT NULL)'
        ).fetchone()[0]
        leer = con.execute(f'SELECT COUNT(*) FROM "{q}" WHERE "{c}" IS NULL').fetchone()[0]
        zeilen.append({"Tabelle": TABELLEN[q]["titel"], "Schlüssel": c, "Verweist auf": TABELLEN[t]["titel"],
                       "Zeilen": n, "Ohne Treffer": waise, "Schlüssel leer": leer})
    dup = int(d["klient"]["klientennr"].duplicated().sum())
    return {"beziehungen": pd.DataFrame(zeilen), "klient_doppelt": dup}


def er_diagramm() -> str:
    """Datenmodell als DOT (für st.graphviz_chart)."""
    knoten = []
    for key, spec in TABELLEN.items():
        farbe = "#15202b" if key == "klient" else ("#0f6e73" if key in ("finanz", "dossierperson") else "#5b6672")
        knoten.append(f'"{key}" [label="{spec["titel"]}", fillcolor="{farbe}"];')
    name = {"zemis": "Zemis-Nr.", "klientennr": "Klientennr.", "dossier": "Dossier-Nr."}
    kanten = [f'"{q}" -> "{t}" [label="{name[c]}"];' for (q, c, t, tc) in BEZIEHUNGEN]
    return ("digraph G { rankdir=LR; bgcolor=transparent; ranksep=1.1; nodesep=0.12; size=\"9,5\"; "
            'node [shape=box, style="rounded,filled", fontcolor=white, fontname="Helvetica", fontsize=10, color="#ffffff", height=0.35, margin="0.12,0.04"]; '
            'edge [color="#9aa6b2", fontname="Helvetica", fontsize=9, fontcolor="#5b6672", arrowsize=0.6]; '
            + " ".join(knoten) + " " + " ".join(kanten) + " }")
