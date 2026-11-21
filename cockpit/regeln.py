"""Regeln für Ziel 1 (Sprache A1) und Datenqualität.

Alle Annahmen stehen oben in REGELN, damit das ASD sie leicht prüfen und ändern kann.
"""
import pandas as pd

REGELN = {
    "status_ziel1": {"VA", "F-FL", "B-FL", "B-RSFL", "B-SL"},   # laut Challenge: VA und FL
    "status_ausgeschlossen": {"S", "N"},
    "mindestalter": 16,
    "frist_jahre_ziel1": 3,
    # ANNAHME: wer erst nach der Einreise 16 wird, hat 3 Jahre ab dem 16. Geburtstag
    "frist_ab_16_geburtstag": True,
    "sprachen": {"deutsch", "französisch"},
    # Nachweis-Arten, die ohne Zertifikat zählen (laut Challenge)
    "art_ohne_zertifikat": {"muttersprache", "schulbesuch in der schweiz", "abgeschlossene ausbildung"},
    "art_zertifikat": "zertifikat",
    "zertifikat_stichworte": ("telc", "fide"),   # laut Challenge
    "rot_tage": 180,          # Frist in weniger als 6 Monaten -> gefährdet
    "gelb_risiko_tage": 365,  # < 12 Monate und noch A0 ohne Kurs -> gefährdet
}

NIVEAU = {"A0": 0, "A1": 1, "A2": 2, "B1": 3, "B2": 4, "C1": 5, "C2": 6}

AMPEL = {
    "Erreicht": "🟢",
    "Erreicht nach Frist": "🟢",
    "Auf Kurs": "🟡",
    "Gefährdet": "🔴",
    "Frist verpasst": "⚫",
    "Nicht anwendbar": "⚪",
}
REIHENFOLGE = ["Gefährdet", "Frist verpasst", "Auf Kurs", "Erreicht", "Erreicht nach Frist", "Nicht anwendbar"]


def _map(keys: pd.Series, werte: pd.Series) -> pd.Series:
    """Wie keys.map(werte), aber robust bei leeren Tabellen und doppelten Schlüsseln."""
    werte = werte[~werte.index.duplicated()]
    return pd.Series(werte.reindex(keys.values).values, index=keys.index)


def _plus_jahre(s: pd.Series, j: int) -> pd.Series:
    return s + pd.DateOffset(years=j)


def aktuelle_klienten(d, stichtag):
    kl = d["klient"].copy()
    st = pd.Timestamp(stichtag)
    aktiv = (kl["zust_ende"].isna() | (kl["zust_ende"] >= st))
    aktiv &= (kl["uebergang_gemeinde"].isna() | (kl["uebergang_gemeinde"] > st))
    aktiv &= (kl["zust_beginn"].isna() | (kl["zust_beginn"] <= st))
    return kl[aktiv].copy()


def status_am_stichtag(d, stichtag) -> pd.Series:
    """Status aus der Historie (gültig am Stichtag); sonst leer."""
    v = d["verfahren"]
    st = pd.Timestamp(stichtag)
    g = v[(v["ab"] <= st) & (v["bis"].isna() | (v["bis"] >= st))]
    g = g.sort_values("ab").groupby("zemis").tail(1)
    return g.set_index("zemis")["status"].astype("string").str.strip()


def einreisedatum(d) -> pd.Series:
    a = d["asylgeschaeft"]
    art = a["art"].astype("string").str.strip()
    e = a[art == "Aufenthalt (Einreise)"].groupby("zemis")["datum"].min()
    g = a[art == "Aufenthalt (Geburt)"].groupby("zemis")["datum"].min()
    return e.combine_first(g)


def a1_nachweise(d) -> pd.DataFrame:
    """Alle Zeilen, die als gültiger A1-Nachweis zählen."""
    s = d["sprache"].copy()
    s["niv"] = s["niveau"].astype("string").str.strip().str.upper().map(NIVEAU)
    s["art_n"] = s["art"].astype("string").str.strip().str.lower()
    s["spr_n"] = s["sprache"].astype("string").str.strip().str.lower()
    bem = s["bemerkungen"].astype("string").str.lower().fillna("")
    hat_stichwort = bem.apply(lambda t: any(w in t for w in REGELN["zertifikat_stichworte"]))
    gueltig_art = s["art_n"].isin(REGELN["art_ohne_zertifikat"]) | (
        (s["art_n"] == REGELN["art_zertifikat"]) & hat_stichwort)
    sprache_ok = s["spr_n"].isin(REGELN["sprachen"]) | (s["art_n"] == "muttersprache")
    ok = s[(s["niv"] >= 1) & gueltig_art & sprache_ok & s["datum"].notna()]
    return ok.sort_values("datum")


def ziel1(d, stichtag) -> pd.DataFrame:
    st = pd.Timestamp(stichtag)
    kl = aktuelle_klienten(d, st)
    stat = status_am_stichtag(d, st)
    kl["status"] = _map(kl["zemis"], stat).fillna(kl["status_aktuell"].astype("string").str.strip())
    kl["einreise"] = _map(kl["zemis"], einreisedatum(d))
    kl["alter"] = ((st - kl["geburtsdatum"]).dt.days // 365.25)
    geb16 = _plus_jahre(kl["geburtsdatum"], REGELN["mindestalter"])
    start = kl["einreise"]
    if REGELN["frist_ab_16_geburtstag"]:
        start = pd.concat([kl["einreise"], geb16], axis=1).max(axis=1)
    kl["frist"] = _plus_jahre(start, REGELN["frist_jahre_ziel1"])
    kl["tage_bis_frist"] = (kl["frist"] - st).dt.days

    # A1-Nachweis: Sprachstand oder offiziell in Integrationszielerreichung
    nw = a1_nachweise(d)
    erster = nw.groupby("zemis").first()
    ze = d["zielerreichung"]
    ze_a1 = ze[ze["art"].astype("string").str.lower().str.contains("sprache", na=False)].groupby("zemis")["datum"].min()
    kl["a1_datum"] = _map(kl["zemis"], erster["datum"]).combine_first(_map(kl["zemis"], ze_a1))
    kl["a1_nachweis"] = _map(kl["zemis"], erster["art"]).astype("string")
    kl["a1_bemerkung"] = _map(kl["zemis"], erster["bemerkungen"]).astype("string")
    kl["gemeldet"] = kl["zemis"].isin(ze_a1.index)

    # aktuelles Niveau (auch Einschätzungen) und laufender Deutschkurs
    s = d["sprache"].copy()
    s["niv"] = s["niveau"].astype("string").str.upper().map(NIVEAU)
    s = s[s["datum"] <= st]
    kl["niveau_aktuell"] = _map(kl["zemis"], s.groupby("zemis")["niv"].max()).map({v: k for k, v in NIVEAU.items()})
    f = d["foerderung"]
    kurs = f[f["art"].astype("string").str.contains("deutsch|alpha|sprach", case=False, na=False)
             & (f["start"] <= st) & (f["abschluss"].isna() | (f["abschluss"] >= st))]
    kl["kurs_laufend"] = kl["zemis"].isin(kurs["zemis"])

    def beurteilen(r):
        if r["status"] in REGELN["status_ausgeschlossen"]:
            return "Nicht anwendbar", f"Status {r['status']} zählt nicht für die Ziele", ""
        if r["status"] not in REGELN["status_ziel1"]:
            return "Nicht anwendbar", f"Status unbekannt ({r['status']})", "Status im System prüfen"
        if pd.isna(r["einreise"]):
            return "Nicht anwendbar", "Einreisedatum fehlt", "Asylgeschäftsdaten prüfen"
        if r["alter"] < REGELN["mindestalter"]:
            return "Nicht anwendbar", f"Unter {REGELN['mindestalter']} Jahre", ""
        if pd.notna(r["a1_datum"]):
            if r["a1_datum"] <= r["frist"]:
                nicht_gemeldet = "" if r["gemeldet"] else "A1 erreicht, aber nicht als Ziel erfasst"
                return "Erreicht", nicht_gemeldet or f"A1 am {r['a1_datum']:%d.%m.%Y}", (
                    "Zielerreichung erfassen" if nicht_gemeldet else "")
            return "Erreicht nach Frist", f"A1 am {r['a1_datum']:%d.%m.%Y}, Frist war {r['frist']:%d.%m.%Y}", ""
        t = r["tage_bis_frist"]
        niv = r["niveau_aktuell"] if pd.notna(r["niveau_aktuell"]) else "unbekannt"
        kurs_txt = "im Deutschkurs" if r["kurs_laufend"] else "kein Deutschkurs"
        if t < 0:
            return "Frist verpasst", f"Frist seit {-t} Tagen vorbei, Niveau {niv}", ""
        if niv in ("A1", "A2", "B1", "B2", "C1", "C2"):
            return "Gefährdet" if t <= REGELN["rot_tage"] else "Auf Kurs", (
                f"Niveau {niv} eingeschätzt, aber kein gültiger Nachweis"), "Zur A1-Prüfung anmelden"
        if t <= 60:
            return "Gefährdet", f"Frist in {t} Tagen, Niveau {niv}, {kurs_txt}", "Sofort Gespräch: Prüfung vor der Frist möglich?"
        if t <= REGELN["rot_tage"]:
            return "Gefährdet", f"Frist in {t} Tagen, Niveau {niv}, {kurs_txt}", (
                "Prüfung planen" if r["kurs_laufend"] else "Deutschkurs sofort organisieren")
        if t <= REGELN["gelb_risiko_tage"] and not r["kurs_laufend"]:
            return "Gefährdet", f"Frist in {t} Tagen, Niveau {niv}, {kurs_txt}", "Deutschkurs organisieren"
        return "Auf Kurs", f"Frist in {t} Tagen, Niveau {niv}, {kurs_txt}", (
            "" if r["kurs_laufend"] else "Kursbesuch prüfen")

    res = kl.apply(beurteilen, axis=1, result_type="expand")
    kl[["stand", "grund", "naechster_schritt"]] = res
    kl["ampel"] = kl["stand"].map(AMPEL) + " " + kl["stand"]
    kl["im_scope"] = kl["stand"] != "Nicht anwendbar"
    kl["einreisejahr"] = kl["einreise"].dt.year.astype("Int64")
    kl["sozialarbeit"] = kl["sozialarbeit"].astype("string").fillna("(nicht zugeteilt)")
    kl["_sort"] = kl["stand"].map({s: i for i, s in enumerate(REIHENFOLGE)})
    return kl.sort_values(["_sort", "tage_bis_frist"]).drop(columns="_sort")


def totale(z1: pd.DataFrame, nach: str) -> pd.DataFrame:
    t = pd.crosstab(z1[nach], z1["stand"]).reindex(columns=REIHENFOLGE, fill_value=0)
    t["Im Scope"] = t[[c for c in REIHENFOLGE if c != "Nicht anwendbar"]].sum(axis=1)
    t.loc["Total"] = t.sum()
    t = t.astype(int)
    t["Quote erreicht"] = (t["Erreicht"] / t["Im Scope"].where(t["Im Scope"] > 0)).round(3)
    t.index = t.index.astype(str)
    t.index.name = {"sozialarbeit": "Fallführung", "einreisejahr": "Einreisejahr"}.get(nach, nach)
    t.columns.name = None
    return t.reset_index()


def datenqualitaet(d, z1: pd.DataFrame, stichtag) -> pd.DataFrame:
    st = pd.Timestamp(stichtag)
    meldungen = []

    def add(kat, zeilen, text, tabelle):
        for _, r in zeilen.iterrows():
            meldungen.append({"Kategorie": kat, "Zemis-Nr.": r.get("zemis"), "Klientennummer": r.get("klientennr"),
                              "Fallführung": r.get("sozialarbeit"), "Hinweis": text(r), "Tabelle": tabelle})

    add("Fehlende Daten", z1[z1["grund"] == "Einreisedatum fehlt"],
        lambda r: "Kein Ereignis «Aufenthalt (Einreise)»", "Asylgeschäftsdaten")
    add("Fehlende Daten", z1[z1["sozialarbeit"] == "(nicht zugeteilt)"],
        lambda r: "Keine Fallführung eingetragen", "Klient")
    add("Geld nicht abgeholt", z1[(z1["stand"] == "Erreicht") & (~z1["gemeldet"])],
        lambda r: f"A1 am {r['a1_datum']:%d.%m.%Y} erreicht, nicht in Integrationszielerreichung", "Integrationszielerreichung")

    s = d["sprache"]
    muster = "|".join(REGELN["zertifikat_stichworte"])
    zert = s[(s["art"].astype("string").str.lower() == "zertifikat")
             & ~s["bemerkungen"].astype("string").str.lower().fillna("").str.contains(muster)]
    zert = zert.merge(z1[["zemis", "klientennr", "sozialarbeit"]], on="zemis", how="inner", suffixes=("_x", ""))
    add("Unklarer Nachweis", zert, lambda r: f"Zertifikat {r['niveau']} ohne telc/fide in Bemerkungen", "Sprachstand")

    zt, ew = d["zemis_taetigkeit"], d["erwerb"]
    m = zt.merge(ew[["zemis", "von", "bis"]], on="zemis", how="left")
    ende_zt = m["bis_x"].fillna(st)
    ende_ew = m["bis_y"].fillna(st)
    m["overlap"] = m["von"].notna() & (m["beginn"] <= ende_ew) & (m["von"] <= ende_zt)
    ohne = m.groupby(["zemis", "beginn", "betrieb"], dropna=False)["overlap"].any().reset_index()
    ohne = ohne[~ohne["overlap"]].merge(z1[["zemis", "klientennr", "sozialarbeit"]], on="zemis", how="inner")
    add("Nicht gemeldete Arbeit?", ohne,
        lambda r: f"ZEMIS: {r['betrieb']} ab {r['beginn']:%d.%m.%Y}, fehlt im Erwerb", "ZEMIS Tätigkeit / Erwerb")
    return pd.DataFrame(meldungen, columns=["Kategorie", "Zemis-Nr.", "Klientennummer", "Fallführung", "Hinweis", "Tabelle"])


# Spalten für Anzeige und Export (deutsche Namen)
EXPORT_SPALTEN = {
    "ampel": "Ampel", "grund": "Grund", "naechster_schritt": "Nächster Schritt",
    "klientennr": "Klientennummer", "zemis": "Zemis-Nr.", "dossier": "Dossier-Nr.",
    "sozialarbeit": "Fallführung", "status": "Verfahrensstand", "alter": "Alter",
    "einreise": "Einreise", "frist": "Frist A1", "tage_bis_frist": "Tage bis Frist",
    "niveau_aktuell": "Niveau aktuell", "kurs_laufend": "Deutschkurs läuft",
    "a1_datum": "A1 erreicht am", "a1_nachweis": "Nachweis", "a1_bemerkung": "Bemerkung Nachweis",
    "gemeldet": "Als Ziel gemeldet",
}


def fuer_anzeige(z1: pd.DataFrame) -> pd.DataFrame:
    out = z1[list(EXPORT_SPALTEN)].rename(columns=EXPORT_SPALTEN).copy()
    out["Alter"] = out["Alter"].astype("Int64")
    out["Tage bis Frist"] = out["Tage bis Frist"].astype("Int64")
    return out
