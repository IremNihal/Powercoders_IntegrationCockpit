"""Ansicht Sozialarbeit (Worklist): «Wen rufe ich diese Woche an, und warum?» – für alle drei Ziele."""
import pandas as pd
import streamlit as st

from cockpit.regeln import fuer_anzeige
from cockpit.ziele23 import anzeige_matrix, anzeige_z2, anzeige_z3
from ansichten import ui, fallakte

ZIEL = {1: "Ziel 1 Sprache", 2: "Ziel 2 Arbeit", 3: "Ziel 3 Haushalt"}
SICHTEN = {"rot": "Gefährdet", "gelb": "Fast geschafft", "gruen": "Zu erfassen"}


def aufgaben(m: pd.DataFrame, z1: pd.DataFrame, z2: pd.DataFrame, z3: pd.DataFrame) -> dict:
    """Sammelt die Arbeitsliste über alle Ziele. Ein Eintrag pro Person (bzw. Haushalt) und Anlass."""
    listen = {"rot": [], "gelb": [], "gruen": []}

    def add(k, tage, zemis, ziel, grund, schritt):
        listen[k].append({"tage": tage, "zemis": zemis, "ziel": ziel, "grund": grund, "schritt": schritt})

    for _, r in z1[z1["im_scope"]].iterrows():
        if r["stand"] == "Gefährdet":
            add("rot", r["tage_bis_frist"], r["zemis"], 1, r["grund"], r["naechster_schritt"])
        elif r["naechster_schritt"] == "Zur A1-Prüfung anmelden":
            add("gelb", r["tage_bis_frist"], r["zemis"], 1, r["grund"], r["naechster_schritt"])
        elif r["stand"] == "Erreicht" and not r["gemeldet"]:
            add("gruen", 0, r["zemis"], 1, r["grund"], "Zielerreichung erfassen")
    for _, r in z2.iterrows():
        t = r["tage_bis_ende"] if pd.notna(r["tage_bis_ende"]) else 9999
        if r["stand"] == "Gefährdet":
            add("rot", t, r["zemis"], 2, r["grund"], r["schritt"])
        elif r["stand"] == "Auf Kurs" and str(r["grund"]).startswith("Stelle ≥ 60 %"):
            add("gelb", t, r["zemis"], 2, r["grund"], r["schritt"])
        elif r["stand"] == "Erreicht" and r["schritt"]:
            add("gruen", 0, r["zemis"], 2, r["grund"], r["schritt"])
    for _, r in z3.iterrows():
        mitglieder = m[m["dossier"] == r["dossier"]]["zemis"]
        if mitglieder.empty:
            continue
        t = r["tage_bis_ende"] if pd.notna(r["tage_bis_ende"]) else 9999
        if r["stand"] == "Gefährdet":
            add("rot", t, mitglieder.iloc[0], 3, r["grund"], r["schritt"])
        elif r["stand"] == "Auf Kurs" and str(r["grund"]).startswith("Seit"):
            add("gelb", t, mitglieder.iloc[0], 3, r["grund"], r["schritt"])
        elif r["stand"] == "Erreicht" and r["schritt"]:
            add("gruen", 0, mitglieder.iloc[0], 3, r["grund"], r["schritt"])
    return {k: sorted(v, key=lambda x: x["tage"]) for k, v in listen.items()}


def zeile(ctx, eintrag, info, klasse, n):
    p = info.loc[eintrag["zemis"]]
    wer = f"Haushalt {p['dossier']}" if eintrag["ziel"] == 3 else f"Klient:in {p['klientennr']}"
    frist = ""
    if klasse != "gruen" and eintrag["tage"] is not None and 0 <= eintrag["tage"] <= 30:
        frist = f'<span class="wl-frist">Frist in {int(eintrag["tage"])} Tagen</span>'
    with st.container(key=f"wl_{klasse}_{n}"):
        a, b, c, e = st.columns([2.1, 3.6, 2.3, 0.9], vertical_alignment="center")
        a.markdown(f'<div class="wl-wer">{wer}<small>{p["status"]}, {int(p["alter"])} Jahre</small></div>',
                   unsafe_allow_html=True)
        b.markdown(f'<span class="wl-ziel">{ZIEL[eintrag["ziel"]]}</span>{frist}<div class="wl-grund">{eintrag["grund"]}</div>',
                   unsafe_allow_html=True)
        if eintrag["schritt"]:
            c.markdown(f'<span class="wl-schritt">{eintrag["schritt"]}</span>', unsafe_allow_html=True)
        if e.button("Öffnen", key=f"open_{klasse}_{n}", type="tertiary", icon=":material/folder_open:"):
            fallakte.oeffnen(ctx, eintrag["zemis"])


def zeigen(ctx):
    d, stichtag, user = ctx["d"], ctx["stichtag"], ctx["user"]
    name = user["name"]
    m = ctx["matrix"][ctx["matrix"]["sozialarbeit"] == name]
    z1 = ctx["z1"][ctx["z1"]["sozialarbeit"] == name]
    z2 = ctx["z2"][ctx["z2"]["sozialarbeit"] == name]
    z3 = ctx["z3"][ctx["z3"]["sozialarbeit"] == name]
    ui.kopf(f"Guten Tag, {name.split()[0]}", "Wen rufe ich diese Woche an, und warum?")
    if m.empty:
        st.info("Für Sie sind keine aktuellen Fälle eingetragen.")
        return
    staende = m[["stand1", "stand2", "stand3"]]
    listen = aufgaben(m, z1, z2, z3)
    ui.kacheln([
        ("Klient:innen", len(m), f"in {m['dossier'].nunique()} Haushalten", None),
        ("Ziele erreicht", int((staende == "Erreicht").sum().sum()), "über alle drei Ziele", "Erreicht"),
        ("Ziele auf Kurs", int((staende == "Auf Kurs").sum().sum()), "Frist gut erreichbar", "Auf Kurs"),
        ("Ziele gefährdet", int((staende == "Gefährdet").sum().sum()), "jetzt handeln", "Gefährdet"),
        ("Zu erfassen", len(listen["gruen"]), "erreicht, Meldung fehlt", None),
    ])

    optionen = [f"{SICHTEN[k]} ({len(listen[k])})" for k in SICHTEN] + [f"Alle Klient:innen ({len(m)})", "Details pro Ziel"]
    wahl = st.segmented_control("Ansicht", optionen, default=optionen[0], key="sa_sicht", label_visibility="collapsed")
    wahl = wahl or optionen[0]
    info = m.set_index("zemis")

    for k, titel in SICHTEN.items():
        if wahl.startswith(titel):
            text = {"rot": "Die dringendsten zuerst. «Öffnen» zeigt die ganze Fallakte.",
                    "gelb": "Mit wenig Aufwand erreichbar: Prüfung anmelden, Stelle halten, Rückfall vermeiden.",
                    "gruen": "Ziel erreicht, aber noch nicht in der Integrationszielerreichung erfasst."}[k]
            ui.abschnitt(titel, text)
            if not listen[k]:
                st.success("Hier ist im Moment nichts zu tun.")
            for n, eintrag in enumerate(listen[k][:25]):
                zeile(ctx, eintrag, info, k, n)
            if len(listen[k]) > 25:
                st.caption(f"{len(listen[k]) - 25} weitere unter «Alle Klient:innen».")

    if wahl.startswith("Alle Klient:innen"):
        ui.abschnitt("Alle Ihre Klient:innen", "Die dringendsten zuerst. Zeile anklicken öffnet die Fallakte.")
        sel = ui.tabelle(anzeige_matrix(m), key="sa_matrix")
        if sel is not None:
            if st.button(f"Fallakte von Klient:in {sel['Klientennummer']} öffnen", key="sa_akte_btn",
                         type="primary", icon=":material/folder_open:"):
                fallakte.oeffnen(ctx, sel["Zemis-Nr."])

    if wahl == "Details pro Ziel":
        ziel = st.segmented_control("Ziel", list(ZIEL.values()), default=ZIEL[1], key="sa_ziel")
        if ziel == ZIEL[2]:
            ui.tabelle(anzeige_z2(z2), key="sa_z2")
        elif ziel == ZIEL[3]:
            ui.tabelle(anzeige_z3(z3), key="sa_z3")
        else:
            ui.tabelle(fuer_anzeige(z1), key="sa_z1")

    st.divider()
    ui.excel_knopf("Meine Liste als Excel herunterladen", {
        "Ampel pro Person": anzeige_matrix(m),
        "Ziel 1 Sprache": fuer_anzeige(z1),
        "Ziel 2 Arbeit": anzeige_z2(z2),
        "Ziel 3 Haushalt": anzeige_z3(z3),
    }, {"Bericht": "Integrations-Cockpit, Ziele 1 bis 3", "Fallführung": name,
        "Stichtag": f"{stichtag:%d.%m.%Y}", "Datenquelle": ctx["quelle"]},
        f"Cockpit_{name.replace(' ', '_')}_{stichtag:%Y%m%d}.xlsx")
