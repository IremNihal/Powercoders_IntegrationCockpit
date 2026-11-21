"""Stufe 2 (Erfolgsfaktoren), Fallbelastung, Was-wäre-wenn 2027."""
import pandas as pd

from .ziele23 import ziel2, ziel3

MIN_GRUPPE = 5   # kleinere Gruppen werden nicht gezeigt (Schutz vor Rückschluss auf Einzelpersonen)
ABGESCHLOSSEN = ["Erreicht", "Erreicht nach Frist", "Frist verpasst"]


def _band(x, grenzen, labels, index=None):
    s = pd.Series(pd.to_numeric(pd.Series(x).values, errors="coerce"), index=index)
    return pd.cut(s, bins=grenzen, labels=labels, right=False).astype("string")


def merkmale(d, z1: pd.DataFrame) -> pd.DataFrame:
    """Merkmale bei Eintritt pro Person (nur Gruppenauswertung, nie Score pro Person)."""
    kl = d["klient"].drop_duplicates("zemis").set_index("zemis")
    m = z1[z1["stand"].isin(ABGESCHLOSSEN)][["zemis", "stand", "einreise", "frist", "geburtsdatum"]].copy()
    m["erfolg"] = m["stand"] == "Erreicht"
    k = kl.reindex(m["zemis"])
    alpha = k["alphabetisiert"].astype("string").str.lower().isin(["true", "ja", "1", "wahr"]).values
    m["Lateinisch alphabetisiert"] = pd.Series(alpha, index=m.index).map({True: "ja", False: "nein"})
    m["Schuljahre vor Einreise"] = _band(k["schuljahre"], [0, 6, 10, 99], ["0–5", "6–9", "10 und mehr"], m.index)
    alter_e = ((m["einreise"] - m["geburtsdatum"]).dt.days / 365.25)
    m["Alter bei Einreise"] = _band(alter_e, [0, 26, 36, 46, 120], ["16–25", "26–35", "36–45", "46 und älter"], m.index)
    m["Muttersprache"] = k["muttersprache"].astype("string").values
    m["Höchste Ausbildung"] = k["ausbildung"].astype("string").values
    m["Arbeitserfahrung vor Einreise"] = _band(k["arbeitsjahre"], [0, 1, 5, 99], ["keine", "1–4 Jahre", "5 und mehr"], m.index)

    f = d["foerderung"].copy()
    f = f[f["art"].astype("string").str.contains("deutsch|alpha|sprach", case=False, na=False)]
    f = f.merge(m[["zemis", "einreise", "frist"]], on="zemis")
    f = f[f["start"] <= f["frist"]]
    erster = f.groupby("zemis")["start"].min()
    std = pd.to_numeric(f["stunden"], errors="coerce").groupby(f["zemis"]).max()
    m["Deutschkurs besucht"] = m["zemis"].isin(erster.index).map({True: "ja", False: "nein"})
    # map() auf eine leere Datums-Serie wirft in pandas 3 (Cast nach float64) – leeren Fall abfangen
    kursbeginn = m["zemis"].map(erster) if not erster.empty else pd.Series(pd.NaT, index=m.index)
    tage = (pd.to_datetime(kursbeginn) - m["einreise"]).dt.days
    m["Kursbeginn nach Einreise"] = pd.cut(tage, [-9999, 183, 365, 99999], labels=["in 6 Monaten", "6–12 Monate", "später"]).astype("string").fillna("kein Kurs")
    m["Kursstunden pro Woche"] = _band(m["zemis"].map(std), [0, 8, 13, 99], ["unter 8", "8–12", "13 und mehr"], m.index).fillna("kein Kurs")
    return m


MERKMALE = ["Lateinisch alphabetisiert", "Schuljahre vor Einreise", "Alter bei Einreise", "Muttersprache",
            "Höchste Ausbildung", "Arbeitserfahrung vor Einreise", "Deutschkurs besucht",
            "Kursbeginn nach Einreise", "Kursstunden pro Woche"]


def erfolgsfaktoren(m: pd.DataFrame, extra: list | tuple = ()):
    """Pro Merkmal: Gruppen mit Anzahl und Quote. Kleine Gruppen werden zusammengefasst oder ausgeblendet.

    extra: zusätzliche Merkmal-Spalten (z.B. aus der Situationsanalyse), die in m vorhanden sind.
    """
    gesamt = m["erfolg"].mean() if len(m) else 0
    tabellen, rang = {}, []
    for mk in [*MERKMALE, *[e for e in extra if e in m.columns]]:
        g = m.groupby(m[mk].fillna("unbekannt"))["erfolg"].agg(["size", "sum"]).rename(columns={"size": "Personen", "sum": "Erreicht"})
        klein = g[g["Personen"] < MIN_GRUPPE]
        g = g[g["Personen"] >= MIN_GRUPPE]
        if klein["Personen"].sum() >= MIN_GRUPPE:
            g.loc["andere (kleine Gruppen)"] = klein.sum()
        g["Quote"] = g["Erreicht"] / g["Personen"]
        g["Differenz"] = g["Quote"] - gesamt
        g = g.reset_index(names="Gruppe")
        tabellen[mk] = g
        if len(g) >= 2:
            rang.append({"Merkmal": mk, "Spannweite": g["Quote"].max() - g["Quote"].min(),
                         "Beste Gruppe": g.loc[g["Quote"].idxmax(), "Gruppe"],
                         "Schwächste Gruppe": g.loc[g["Quote"].idxmin(), "Gruppe"]})
    rang = pd.DataFrame(rang).sort_values("Spannweite", ascending=False) if rang else pd.DataFrame()
    return gesamt, tabellen, rang


def fallbelastung(z1: pd.DataFrame, matrix: pd.DataFrame) -> pd.DataFrame:
    rot = matrix[["stand1", "stand2", "stand3"]].eq("Gefährdet").any(axis=1)
    aktiv = matrix[["stand1", "stand2", "stand3"]].isin(["Auf Kurs", "Gefährdet"]).any(axis=1)
    t = pd.DataFrame({
        "Fallführung": matrix["sozialarbeit"],
        "Personen": 1,
        "Haushalt": matrix["dossier"],
        "Offene Ziele": aktiv.astype(int),
        "Mit roter Ampel": rot.astype(int),
    }).groupby("Fallführung").agg(Personen=("Personen", "sum"), Haushalte=("Haushalt", "nunique"),
                                  **{"Offene Ziele": ("Offene Ziele", "sum"), "Mit roter Ampel": ("Mit roter Ampel", "sum")})
    t["Anteil rot"] = t["Mit roter Ampel"] / t["Personen"]
    return t.sort_values("Personen", ascending=False).reset_index()


def szenario_2027(d, stichtag, z2_jetzt: pd.DataFrame, z3_jetzt: pd.DataFrame):
    """ANNAHME: Ab 01.01.2027 endet die Zuständigkeit für VA / F-FL 5 statt 7 Jahre nach Einreise,
    frühestens am 01.01.2027. Andere Status bleiben gleich."""
    stichtag_2027 = pd.Timestamp("2027-01-01")
    d2 = dict(d)
    kl = d["klient"].copy()
    a = d["asylgeschaeft"]
    einreise = a[a["art"].astype("string") == "Aufenthalt (Einreise)"].groupby("zemis")["datum"].min()
    stat = kl["status_aktuell"].astype("string").str.strip()
    betroffen = stat.isin(["VA", "F-FL"])
    neu = (kl["zemis"].map(einreise) + pd.DateOffset(years=5)).clip(lower=stichtag_2027)
    kl["zust_ende_neu"] = kl["zust_ende"].where(~betroffen, pd.concat([kl["zust_ende"], neu], axis=1).min(axis=1))
    st = pd.Timestamp(stichtag)
    aktuell = (kl["zust_ende"] >= st) & (kl["uebergang_gemeinde"].isna() | (kl["uebergang_gemeinde"] > st))
    frueher = kl[betroffen & aktuell & (kl["zust_ende_neu"] < kl["zust_ende"])]
    kl["zust_ende"] = kl["zust_ende_neu"]
    d2["klient"] = kl.drop(columns="zust_ende_neu")
    z2n = ziel2(d2, stichtag)
    z3n = ziel3(d2, stichtag)

    def vergleich(alt, neu_, key):
        v = alt[[key, "stand"]].merge(neu_[[key, "stand"]], on=key, suffixes=(" heute", " ab 2027"))
        return pd.crosstab(v["stand heute"], v["stand ab 2027"])

    personen = frueher[["klientennr", "zemis", "dossier", "sozialarbeit", "status_aktuell", "zust_ende"]].copy()
    personen["zust_ende_2027"] = kl.loc[frueher.index, "zust_ende"]
    personen["Monate früher"] = ((personen["zust_ende"] - personen["zust_ende_2027"]).dt.days / 30.4).round(0).astype(int)
    return {
        "personen": personen,
        "z2_vergleich": vergleich(z2_jetzt, z2n, "zemis"),
        "z3_vergleich": vergleich(z3_jetzt, z3n, "dossier"),
        "z2_neu": z2n, "z3_neu": z3n,
    }
