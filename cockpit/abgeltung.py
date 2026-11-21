"""Zielerreichung und Abgeltung.

Hintergrund (Kanton Bern, NA-BE): Der regionale Partner erhält bei der Zuweisung nur einen Teil
der Integrationspauschale. Der Rest wird pro erreichtem Ziel ausbezahlt (A1, Ausbildung/Arbeit,
Ablösung von der Sozialhilfe). Ein erreichtes, aber nicht erfasstes Ziel ist also Geld, das fehlt.
Die Beträge pro Ziel stehen im Leistungsvertrag und sind nicht öffentlich – darum rechnet das
Cockpit in Anzahl Zielen; ein Betrag pro Ziel kann optional eingegeben werden.
"""
import pandas as pd


def kennzahlen(d, z1: pd.DataFrame, stichtag) -> dict:
    st = pd.Timestamp(stichtag)
    ze = d["zielerreichung"]
    a1 = ze[ze["art"].astype("string").str.lower().str.contains("sprache", na=False)]
    jahr = a1[a1["datum"].dt.year == st.year]
    sc = z1[z1["im_scope"]]
    offen = sc[sc["stand"].isin(["Gefährdet", "Auf Kurs"])]
    return {
        "gemeldet_jahr": len(jahr),
        "nicht_gemeldet": int(((sc["stand"] == "Erreicht") & ~sc["gemeldet"]).sum()),
        "moeglich_12": int((offen["tage_bis_frist"] <= 365).sum()),
        "moeglich_total": len(offen),
        "gefaehrdet": int((offen["stand"] == "Gefährdet").sum()),
        "verpasst": int((sc["stand"] == "Frist verpasst").sum()),
        "quick_win": int(sc["naechster_schritt"].eq("Zur A1-Prüfung anmelden").sum()),
    }


def verlauf(z1: pd.DataFrame, stichtag, monate=24) -> pd.DataFrame:
    """A1 erreicht (in Frist) pro Monat, letzte N Monate."""
    st = pd.Timestamp(stichtag)
    start = (st - pd.DateOffset(months=monate - 1)).to_period("M").to_timestamp()
    e = z1[z1["stand"].eq("Erreicht") & z1["a1_datum"].ge(start) & z1["a1_datum"].le(st)]
    zaehl = e["a1_datum"].dt.to_period("M").dt.to_timestamp().value_counts()
    idx = pd.date_range(start, periods=monate, freq="MS")
    return pd.DataFrame({"Monat": idx, "A1 erreicht": zaehl.reindex(idx, fill_value=0).values})
