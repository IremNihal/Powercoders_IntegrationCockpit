"""Ziel 2 (Arbeit / Ausbildung) und Ziel 3 (12 Monate ohne Sozialhilfe, pro Haushalt).

Regeln laut Challenge:
  Ziel 2: VA und FL ab 16. Arbeit ≥ 60 % während 6 Monaten ohne Unterbruch, oder Ausbildung Sek II / Tertiär.
          Frist: vor Zuständigkeitsende.
  Ziel 3: Haushalt (Dossier-Nr.). 12 Monate ohne Sozialhilfe für den ganzen Haushalt. Frist: vor Zuständigkeitsende.
Annahmen sind in REGELN23 markiert.
"""
import pandas as pd

from .regeln import REGELN, AMPEL, REIHENFOLGE, aktuelle_klienten, status_am_stichtag, einreisedatum, _map

REGELN23 = {
    "min_pensum": 60,
    "min_tage_arbeit": 183,            # 6 Monate
    "max_luecke_tage": 1,              # ANNAHME: neue Stelle am Folgetag = ohne Unterbruch
    "ausbildung_arten": {"sek ii", "tertiär", "tertiaer"},
    "unterstuetzt_arten": {"sozialhilfe", "nothilfe"},   # ANNAHME: Nothilfe zählt wie Sozialhilfe
    "tage_ohne_sh": 365,
    "rot_tage_z2": 365,                # weniger als 12 Mt. bis Zuständigkeitsende ohne Aktivität -> gefährdet
    "rot_tage_z3": 540,                # weniger als 18 Mt. und noch unterstützt -> gefährdet
}


def _basis(d, stichtag):
    st = pd.Timestamp(stichtag)
    kl = aktuelle_klienten(d, st)
    stat = status_am_stichtag(d, st)
    kl["status"] = _map(kl["zemis"], stat).fillna(kl["status_aktuell"].astype("string").str.strip())
    kl["einreise"] = _map(kl["zemis"], einreisedatum(d))
    kl["alter"] = (st - kl["geburtsdatum"]).dt.days // 365.25
    kl["sozialarbeit"] = kl["sozialarbeit"].astype("string").fillna("(nicht zugeteilt)")
    kl["tage_bis_ende"] = (kl["zust_ende"] - st).dt.days
    return kl


def _zusammenhaengend(perioden: pd.DataFrame, stichtag) -> pd.DataFrame:
    """Fügt Perioden ohne Unterbruch zusammen. Erwartet Spalten von, bis (bis leer = läuft)."""
    st = pd.Timestamp(stichtag)
    p = perioden.dropna(subset=["von"]).sort_values("von")
    bloecke = []
    for _, r in p.iterrows():
        ende = r["bis"] if pd.notna(r["bis"]) else st
        if bloecke and r["von"] <= bloecke[-1][1] + pd.Timedelta(days=REGELN23["max_luecke_tage"] + 1):
            bloecke[-1][1] = max(bloecke[-1][1], ende)
            bloecke[-1][2] = bloecke[-1][2] or pd.isna(r["bis"])
        else:
            bloecke.append([r["von"], ende, pd.isna(r["bis"])])
    return pd.DataFrame(bloecke, columns=["von", "bis", "laeuft"])


def ziel2(d, stichtag) -> pd.DataFrame:
    st = pd.Timestamp(stichtag)
    kl = _basis(d, st)
    ew = d["erwerb"].copy()
    ew["pensum_n"] = pd.to_numeric(ew["pensum"], errors="coerce")
    gross = ew[ew["pensum_n"] >= REGELN23["min_pensum"]]
    f = d["foerderung"]
    art = f["art"].astype("string").str.strip().str.lower()
    ausb = f[art.isin(REGELN23["ausbildung_arten"]) & (f["start"] <= st)].groupby("zemis")["start"].min()
    vorbereitung = f[art.str.contains("brücken|vorlehre|integrationsprogramm|arbeitsintegration", na=False)
                     & (f["start"] <= st) & (f["abschluss"].isna() | (f["abschluss"] >= st))]["zemis"]
    ze = d["zielerreichung"]
    ze2 = ze[ze["art"].astype("string").str.lower().str.contains("erwerb|ausbildung|arbeit", na=False)]
    gemeldet = set(ze2["zemis"])

    zeilen = []
    for _, r in kl.iterrows():
        z = r["zemis"]
        info = {"zemis": z, "datum": pd.NaT, "detail": ""}
        if r["status"] in REGELN["status_ausgeschlossen"] or r["status"] not in REGELN["status_ziel1"]:
            zeilen.append({**info, "stand": "Nicht anwendbar", "grund": f"Status {r['status']} zählt nicht", "schritt": ""})
            continue
        if r["alter"] < REGELN["mindestalter"]:
            zeilen.append({**info, "stand": "Nicht anwendbar", "grund": "Unter 16 Jahre", "schritt": ""})
            continue
        frist = r["zust_ende"]
        # Ausbildung
        if z in ausb.index and (pd.isna(frist) or ausb[z] <= frist):
            zeilen.append({**info, "datum": ausb[z], "stand": "Erreicht",
                           "grund": f"Ausbildung Sek II / Tertiär seit {ausb[z]:%d.%m.%Y}",
                           "schritt": "" if z in gemeldet else "Zielerreichung erfassen", "detail": "Ausbildung"})
            continue
        # Arbeit
        bl = _zusammenhaengend(gross[gross["zemis"] == z][["von", "bis"]], st)
        if not bl.empty and pd.notna(frist):
            bl["bis"] = bl["bis"].clip(upper=frist)
        bl["tage"] = (bl["bis"] - bl["von"]).dt.days if not bl.empty else []
        ok = bl[bl["tage"] >= REGELN23["min_tage_arbeit"]] if not bl.empty else bl
        if not ok.empty:
            dat = ok.iloc[0]["von"] + pd.Timedelta(days=REGELN23["min_tage_arbeit"])
            zeilen.append({**info, "datum": dat, "stand": "Erreicht",
                           "grund": f"6 Monate Arbeit ≥ 60 % erreicht am {dat:%d.%m.%Y}",
                           "schritt": "" if z in gemeldet else "Zielerreichung erfassen", "detail": "Arbeit"})
            continue
        rest = r["tage_bis_ende"]
        laufend = bl[bl["laeuft"]] if not bl.empty else bl
        if not laufend.empty:
            schon = int(laufend.iloc[-1]["tage"])
            fehlt = REGELN23["min_tage_arbeit"] - schon
            if pd.isna(rest) or fehlt <= rest:
                zeilen.append({**info, "stand": "Auf Kurs", "grund": f"Stelle ≥ 60 % seit {schon} Tagen, noch {fehlt} Tage",
                               "schritt": "Stelle sichern, Unterbruch vermeiden"})
            else:
                zeilen.append({**info, "stand": "Gefährdet", "grund": f"Stelle läuft, aber nur noch {rest} Tage bis Zuständigkeitsende",
                               "schritt": "Ausbildung prüfen"})
            continue
        klein = ew[(ew["zemis"] == z) & (ew["bis"].isna() | (ew["bis"] >= st)) & (ew["pensum_n"] < REGELN23["min_pensum"])]
        if pd.notna(rest) and rest < REGELN23["min_tage_arbeit"]:
            zeilen.append({**info, "stand": "Gefährdet", "grund": f"Nur noch {rest} Tage, 6 Monate Arbeit nicht mehr möglich",
                           "schritt": "Nur noch über Ausbildung erreichbar"})
        elif not klein.empty:
            p = int(klein["pensum_n"].max())
            zeilen.append({**info, "stand": "Auf Kurs" if (pd.isna(rest) or rest > REGELN23["rot_tage_z2"]) else "Gefährdet",
                           "grund": f"Arbeitet {p} %, braucht 60 %", "schritt": "Pensum erhöhen"})
        elif z in set(vorbereitung):
            zeilen.append({**info, "stand": "Auf Kurs", "grund": "In Brückenangebot / Vorbereitung",
                           "schritt": "Anschlusslösung planen"})
        elif pd.notna(rest) and rest <= REGELN23["rot_tage_z2"]:
            zeilen.append({**info, "stand": "Gefährdet", "grund": f"Keine Arbeit, keine Ausbildung, noch {rest} Tage",
                           "schritt": "Stellensuche / Integrationsprogramm"})
        else:
            zeilen.append({**info, "stand": "Auf Kurs", "grund": f"Noch keine Arbeit, {int(rest) if pd.notna(rest) else '?'} Tage Zeit",
                           "schritt": "Potenzial abklären"})
    out = pd.DataFrame(zeilen)
    return kl[["zemis", "klientennr", "dossier", "sozialarbeit", "status", "alter", "einreise", "zust_ende",
               "tage_bis_ende"]].merge(out, on="zemis")


def ziel3(d, stichtag) -> pd.DataFrame:
    """Pro Haushalt (Dossier-Nr.). Gibt eine Zeile pro Dossier zurück."""
    st = pd.Timestamp(stichtag)
    kl = _basis(d, st)
    fu = d["finanz"].copy()
    fu["unterstuetzt"] = fu["art"].astype("string").str.strip().str.lower().isin(REGELN23["unterstuetzt_arten"])
    ze = d["zielerreichung"]
    ze3 = ze[ze["art"].astype("string").str.lower().str.contains("ablösung|sozialhilfe", na=False)]
    gemeldet_zemis = set(ze3["zemis"])
    ew = d["erwerb"]
    erwerb_jetzt = set(ew[(ew["von"] <= st) & (ew["bis"].isna() | (ew["bis"] >= st))]["zemis"])

    zeilen = []
    for dossier, mitglieder in kl.groupby("dossier"):
        relevant = mitglieder[mitglieder["status"].isin(REGELN["status_ziel1"])]
        frist = mitglieder["zust_ende"].max()
        rest = (frist - st).days if pd.notna(frist) else None
        base = {"dossier": dossier, "sozialarbeit": mitglieder["sozialarbeit"].mode().iloc[0],
                "personen": len(mitglieder), "zust_ende": frist, "tage_bis_ende": rest, "datum": pd.NaT,
                "tage_ohne_sh": None}
        if relevant.empty:
            zeilen.append({**base, "stand": "Nicht anwendbar", "grund": "Kein VA/FL im Haushalt", "schritt": ""})
            continue
        perioden = fu[(fu["dossier"] == dossier) & fu["unterstuetzt"]][["von", "bis"]]
        if perioden.empty:
            zeilen.append({**base, "stand": "Nicht anwendbar", "grund": "Keine Unterstützungsdaten", "schritt": "Finanzdaten prüfen"})
            continue
        bl = _zusammenhaengend(perioden, st)
        gemeldet = bool(set(mitglieder["zemis"]) & gemeldet_zemis)
        # Lücken ohne Sozialhilfe (zwischen Blöcken und nach dem letzten)
        erreicht = None
        for i in range(len(bl)):
            ende = bl.iloc[i]["bis"]
            if bl.iloc[i]["laeuft"]:
                break
            naechst = bl.iloc[i + 1]["von"] if i + 1 < len(bl) else st
            grenze = min(naechst, frist) if pd.notna(frist) else naechst
            if (grenze - ende).days >= REGELN23["tage_ohne_sh"]:
                erreicht = ende + pd.Timedelta(days=REGELN23["tage_ohne_sh"])
                break
        if erreicht is not None:
            zeilen.append({**base, "datum": erreicht, "stand": "Erreicht",
                           "grund": f"12 Monate ohne Sozialhilfe am {erreicht:%d.%m.%Y}",
                           "schritt": "" if gemeldet else "Zielerreichung erfassen"})
            continue
        letzter = bl.iloc[-1]
        if not letzter["laeuft"]:
            ohne = (st - letzter["bis"]).days
            fehlt = REGELN23["tage_ohne_sh"] - ohne
            base["tage_ohne_sh"] = ohne
            if rest is None or fehlt <= rest:
                zeilen.append({**base, "stand": "Auf Kurs", "grund": f"Seit {ohne} Tagen ohne Sozialhilfe, noch {fehlt} Tage",
                               "schritt": "Rückfall vermeiden"})
            else:
                zeilen.append({**base, "stand": "Frist verpasst",
                               "grund": f"Seit {ohne} Tagen ohne Sozialhilfe, 12 Monate vor Zuständigkeitsende ({rest} Tage) nicht mehr möglich",
                               "schritt": ""})
            continue
        if rest is not None and rest < REGELN23["tage_ohne_sh"]:
            zeilen.append({**base, "stand": "Frist verpasst", "grund": f"Noch unterstützt, nur noch {rest} Tage bis Zuständigkeitsende",
                           "schritt": ""})
        elif rest is not None and rest < REGELN23["rot_tage_z3"]:
            zeilen.append({**base, "stand": "Gefährdet", "grund": f"Noch unterstützt, {rest} Tage bis Zuständigkeitsende",
                           "schritt": "Einkommen im Haushalt stärken"})
        else:
            verdiener = set(mitglieder["zemis"]) & erwerb_jetzt
            if verdiener:
                zeilen.append({**base, "stand": "Auf Kurs", "grund": f"Noch unterstützt, Erwerbseinkommen im Haushalt, {rest} Tage Zeit",
                               "schritt": "Ablösung prüfen"})
            else:
                zeilen.append({**base, "stand": "Auf Kurs", "grund": f"Noch unterstützt, kein Erwerbseinkommen, {rest} Tage Zeit",
                               "schritt": "Arbeitsintegration im Haushalt planen"})
    return pd.DataFrame(zeilen)


def ampel_matrix(z1: pd.DataFrame, z2: pd.DataFrame, z3: pd.DataFrame) -> pd.DataFrame:
    """Eine Zeile pro Person, Ampel für Ziel 1, 2, 3 (Ziel 3 vom Haushalt)."""
    m = z1[["zemis", "klientennr", "dossier", "sozialarbeit", "status", "alter", "stand", "grund", "naechster_schritt"]].rename(
        columns={"stand": "stand1", "grund": "grund1", "naechster_schritt": "schritt1"})
    m = m.merge(z2[["zemis", "stand", "grund", "schritt"]].rename(columns={"stand": "stand2", "grund": "grund2", "schritt": "schritt2"}),
                on="zemis", how="left")
    m = m.merge(z3[["dossier", "stand", "grund", "schritt"]].rename(columns={"stand": "stand3", "grund": "grund3", "schritt": "schritt3"}),
                on="dossier", how="left")
    for i in (1, 2, 3):
        m[f"stand{i}"] = m[f"stand{i}"].fillna("Nicht anwendbar")
        m[f"ampel{i}"] = m[f"stand{i}"].map(AMPEL)
    rang = {s: i for i, s in enumerate(REIHENFOLGE)}
    m["_prio"] = m[["stand1", "stand2", "stand3"]].apply(lambda r: min(rang[x] for x in r), axis=1)
    return m.sort_values(["_prio", "klientennr"]).drop(columns="_prio")


def anzeige_z2(z2: pd.DataFrame) -> pd.DataFrame:
    out = z2.assign(Ampel=z2["stand"].map(AMPEL) + " " + z2["stand"])[
        ["Ampel", "grund", "schritt", "klientennr", "zemis", "dossier", "sozialarbeit", "status", "alter", "zust_ende", "tage_bis_ende", "datum"]]
    out = out.rename(columns={"grund": "Grund", "schritt": "Nächster Schritt", "klientennr": "Klientennummer", "zemis": "Zemis-Nr.",
                              "dossier": "Dossier-Nr.", "sozialarbeit": "Fallführung", "status": "Verfahrensstand", "alter": "Alter",
                              "zust_ende": "Zuständigkeitsende", "tage_bis_ende": "Tage bis Ende", "datum": "Erreicht am"})
    out["Alter"] = out["Alter"].astype("Int64")
    return out


def anzeige_z3(z3: pd.DataFrame) -> pd.DataFrame:
    out = z3.assign(Ampel=z3["stand"].map(AMPEL) + " " + z3["stand"])[
        ["Ampel", "grund", "schritt", "dossier", "sozialarbeit", "personen", "zust_ende", "tage_bis_ende", "tage_ohne_sh", "datum"]]
    return out.rename(columns={"grund": "Grund", "schritt": "Nächster Schritt", "dossier": "Dossier-Nr.", "sozialarbeit": "Fallführung",
                               "personen": "Personen im Haushalt", "zust_ende": "Zuständigkeitsende", "tage_bis_ende": "Tage bis Ende",
                               "tage_ohne_sh": "Tage ohne Sozialhilfe", "datum": "Erreicht am"})


def anzeige_matrix(m: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame({
        "Klientennummer": m["klientennr"], "Zemis-Nr.": m["zemis"], "Dossier-Nr.": m["dossier"],
        "Fallführung": m["sozialarbeit"], "Verfahrensstand": m["status"], "Alter": m["alter"].astype("Int64"),
        "Ziel 1 Sprache": m["ampel1"] + " " + m["stand1"], "Ziel 2 Arbeit": m["ampel2"] + " " + m["stand2"],
        "Ziel 3 Haushalt": m["ampel3"] + " " + m["stand3"],
        "Grund Ziel 1": m["grund1"], "Grund Ziel 2": m["grund2"], "Grund Ziel 3": m["grund3"],
    })
    return out
