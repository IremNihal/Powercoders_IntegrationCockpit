"""Ansicht Leitung: alle drei Ziele, Erfolgsfaktoren, Fallbelastung, Abgeltung, Regeländerung 2027."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cockpit.regeln import totale, fuer_anzeige, REIHENFOLGE
from cockpit.ziele23 import anzeige_matrix, anzeige_z2, anzeige_z3
from cockpit import abgeltung, analysen, daten, situationsanalyse
from ansichten import ui
from ansichten import fallakte
from ansichten.sozialarbeit import ZIEL, aufgaben, zeile as wl_zeile

STAENDE = ["Erreicht", "Erreicht nach Frist", "Auf Kurs", "Gefährdet", "Frist verpasst"]
CFG = {"displayModeBar": False}


def filter_leiste(ctx):
    m = ctx["matrix"]
    c1, c2, c3, c4 = st.columns([1.3, 1, 1, 0.6])
    sa = c1.multiselect("Fallführung", sorted(m["sozialarbeit"].unique()), placeholder="Alle", key="f_sa")
    jahre = sorted(ctx["z1"]["einreisejahr"].dropna().astype(int).unique())
    jj = c2.multiselect("Einreisejahr", jahre, placeholder="Alle", key="f_jahr")
    stat = c3.multiselect("Verfahrensstand", sorted(m["status"].dropna().unique()), placeholder="Alle", key="f_stat")
    z1 = ctx["z1"]
    if sa:
        z1 = z1[z1["sozialarbeit"].isin(sa)]
    if jj:
        z1 = z1[z1["einreisejahr"].isin(jj)]
    if stat:
        z1 = z1[z1["status"].isin(stat)]
    ids, doss = set(z1["zemis"]), set(z1["dossier"])
    c4.markdown(f"<div style='padding-top:30px;color:#5b6672'>{len(ids)} Personen</div>", unsafe_allow_html=True)
    return {"z1": z1, "z2": ctx["z2"][ctx["z2"]["zemis"].isin(ids)], "z3": ctx["z3"][ctx["z3"]["dossier"].isin(doss)],
            "matrix": m[m["zemis"].isin(ids)]}


def gruppen_chart(tab: pd.DataFrame, gesamt: float):
    tab = tab.sort_values("Quote", ascending=True)
    fig = go.Figure()
    fig.add_bar(y=tab["Gruppe"], x=tab["Quote"], orientation="h", marker=dict(color=ui.AARE),
                text=[f"{q:.0%}  (n={n})" for q, n in zip(tab["Quote"], tab["Personen"])], textposition="outside",
                cliponaxis=False, hovertemplate="%{y}: %{x:.0%}<extra></extra>")
    fig.add_vline(x=gesamt, line=dict(color="#15202b", width=1.5, dash="dot"),
                  annotation_text=f"alle: {gesamt:.0%}", annotation_position="top")
    fig = ui._layout(fig, 70 + 44 * len(tab))
    fig.update_xaxes(tickformat=".0%", range=[0, 1.15])
    fig.update_yaxes(type="category")
    fig.update_layout(showlegend=False, margin=dict(l=8, r=40, t=30, b=8))
    return fig



def ist_soll(z1: pd.DataFrame, stichtag, nach: str, titel: str) -> pd.DataFrame:
    """Soll = Frist bis Stichtag abgelaufen (hätte A1 haben sollen). Ist = davon in der Frist erreicht."""
    st_ = pd.Timestamp(stichtag)
    sc = z1[z1["im_scope"]].copy()
    sc["soll"] = sc["frist"] <= st_
    sc["ist"] = sc["soll"] & (sc["stand"] == "Erreicht")
    sc["offen"] = sc["frist"] > st_
    sc["frueh"] = sc["offen"] & (sc["stand"] == "Erreicht")
    g = sc.groupby(sc[nach].astype("string").fillna("unbekannt"))
    t = pd.DataFrame({
        "Betroffen": g.size(),
        "Soll (Frist abgelaufen)": g["soll"].sum(),
        "Ist (A1 in Frist)": g["ist"].sum(),
        "Frist noch offen": g["offen"].sum(),
        "davon A1 schon erreicht": g["frueh"].sum(),
    }).astype(int)
    t.loc["Total"] = t.sum()
    t["Lücke (hätte A1 haben sollen)"] = t["Soll (Frist abgelaufen)"] - t["Ist (A1 in Frist)"]
    t["Ist/Soll"] = (t["Ist (A1 in Frist)"] / t["Soll (Frist abgelaufen)"].where(t["Soll (Frist abgelaufen)"] > 0)).round(3)
    t.index.name = titel
    return t.reset_index()


def stufe1(ctx, z1: pd.DataFrame):
    stichtag = ctx["stichtag"]
    st_ = pd.Timestamp(stichtag)
    sc = z1[z1["im_scope"]]
    nicht = z1[~z1["im_scope"]]
    soll = sc[sc["frist"] <= st_]
    ist = soll[soll["stand"] == "Erreicht"]
    luecke = soll[soll["stand"] != "Erreicht"]
    erreicht_alle = sc[sc["stand"].isin(["Erreicht", "Erreicht nach Frist"])]
    ui.kacheln([
        ("1 · Wer ist betroffen?", len(sc), f"von {len(z1)} aktuellen Klient:innen", None),
        ("2 · Frist abgelaufen (Soll)", len(soll), "hätten A1 bis heute haben sollen", None),
        ("3 · Wer hat A1 erreicht?", len(erreicht_alle), f"{int((sc['stand'] == 'Erreicht').sum())} davon in der Frist", "Erreicht"),
        ("4 · Hätte A1 haben sollen", len(luecke), f"Ist/Soll {len(ist) / max(1, len(soll)):.0%}", "Gefährdet"),
    ])

    ui.abschnitt("1 · Wer ist betroffen?",
                 "Aktuelle Klient:innen mit Status VA oder FL (B-FL, B-RSFL, B-SL, F-FL), ab 16 Jahren. Status S und N zählen nicht.")
    grund = nicht["grund"].str.replace(r"Status (\S+) .*", r"Status \1", regex=True).value_counts()
    a, b = st.columns([1, 1.3])
    a.dataframe(pd.DataFrame({"Nicht betroffen, weil": grund.index, "Personen": grund.values}),
                hide_index=True, width="stretch")
    sstat = sc["status"].value_counts()
    b.dataframe(pd.DataFrame({"Betroffen nach Status": sstat.index, "Personen": sstat.values}),
                hide_index=True, width="stretch")

    ui.abschnitt("2 · Welche Frist gilt?",
                 "3 Jahre ab Einreise (Ereignis «Aufenthalt (Einreise)»). Annahme: wer erst später 16 wird, ab dem 16. Geburtstag.")
    fr = sc.dropna(subset=["frist"]).copy()
    fr["Quartal"] = fr["frist"].dt.to_period("Q").astype(str)
    fr["Lage"] = (fr["frist"] <= st_).map({True: "Frist abgelaufen", False: "Frist offen"})
    tab = pd.crosstab(fr["Quartal"], fr["Lage"]).reindex(columns=["Frist abgelaufen", "Frist offen"], fill_value=0).reset_index()
    fig = go.Figure()
    fig.add_bar(x=tab["Quartal"], y=tab["Frist abgelaufen"], name="Frist abgelaufen",
                marker=dict(color="#9aa6b2", line=dict(color="#fff", width=1)))
    fig.add_bar(x=tab["Quartal"], y=tab["Frist offen"], name="Frist offen",
                marker=dict(color=ui.AARE, line=dict(color="#fff", width=1)))
    fig = ui._layout(fig, 260)
    fig.update_xaxes(type="category")
    st.plotly_chart(fig, width="stretch", config=CFG)

    ui.abschnitt("3 · Wer hat A1 erreicht?", "Nachweis: Zertifikat telc/fide, Muttersprache, Schulbesuch in der Schweiz, "
                 "abgeschlossene Ausbildung, oder erfasst in der Integrationszielerreichung.")
    nw = erreicht_alle["a1_nachweis"].fillna("nur in Integrationszielerreichung").value_counts()
    a, b = st.columns([1, 1.3])
    a.dataframe(pd.DataFrame({"Nachweis": nw.index, "Personen": nw.values}), hide_index=True, width="stretch")
    b.dataframe(pd.DataFrame({"Stand": ["In der Frist erreicht", "Nach der Frist erreicht"],
                              "Personen": [int((sc["stand"] == "Erreicht").sum()), int((sc["stand"] == "Erreicht nach Frist").sum())]}),
                hide_index=True, width="stretch")

    ui.abschnitt("4 · Wer hätte A1 inzwischen erreichen sollen?",
                 f"Frist bis {st_:%d.%m.%Y} abgelaufen, aber kein Nachweis in der Frist ({len(luecke)} Personen).")
    ui.tabelle(fuer_anzeige(luecke), key="s1_luecke", hoehe=min(380, 38 * (len(luecke) + 1)))

    quote = st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)
    t_sa = ist_soll(z1, stichtag, "sozialarbeit", "Fallführung")
    t_jahr = ist_soll(z1, stichtag, "einreisejahr", "Einreisejahr")
    ui.abschnitt("Total pro Sozialarbeiter:in", "Soll = Frist abgelaufen. Ist = davon A1 in der Frist.")
    st.dataframe(t_sa, hide_index=True, width="stretch", column_config={"Ist/Soll": quote})
    ui.abschnitt("Total pro Einreisejahr")
    st.dataframe(t_jahr, hide_index=True, width="stretch", column_config={"Ist/Soll": quote})

    ui.abschnitt("Alle Personen mit Ziel 1", "Pro Person: Status, Frist, Nachweis, Stand. Zeile anklicken öffnet die Fallakte.")
    sel = ui.tabelle(fuer_anzeige(sc), key="s1_alle")
    if sel is not None:
        if st.button(f"Fallakte von Klient:in {sel['Klientennummer']} öffnen", key="s1_akte_btn",
                     type="primary", icon=":material/folder_open:"):
            fallakte.oeffnen(ctx, sel["Zemis-Nr."])
    ui.excel_knopf("Stufe 1 als Excel herunterladen", {
        "Pro Person": fuer_anzeige(z1),
        "Hätte A1 haben sollen": fuer_anzeige(luecke),
        "Total pro Sozialarbeiter:in": t_sa,
        "Total pro Einreisejahr": t_jahr,
    }, {"Bericht": "Stufe 1: Ist-Soll-Vergleich Ziel 1 (Sprache A1)", "Stichtag": f"{st_:%d.%m.%Y}",
        "Datenquelle": ctx["quelle"], "Soll": "Personen, deren Frist bis zum Stichtag abgelaufen ist",
        "Ist": "davon A1 in der Frist erreicht"}, f"Stufe1_Ziel1_{st_:%Y%m%d}.xlsx")

def zeigen(ctx):
    d, stichtag = ctx["d"], ctx["stichtag"]
    ui.kopf("Integrationsziele", "Alle aktuellen Klient:innen des Asylsozialdienstes")
    f = filter_leiste(ctx)
    z1, z2, z3, m = f["z1"], f["z2"], f["z3"], f["matrix"]
    staende = m[["stand1", "stand2", "stand3"]]
    nicht_erfasst = (int(((z1["stand"] == "Erreicht") & ~z1["gemeldet"]).sum())
                     + int((z2["schritt"] == "Zielerreichung erfassen").sum())
                     + int((z3["schritt"] == "Zielerreichung erfassen").sum()))

    haupt = st.tabs(["Stufe 1: Ziel 1 Ist/Soll", "Überblick alle Ziele", "Abgeltung & Erfassung", "Erfolgsfaktoren"])
    with haupt[0]:
        stufe1(ctx, z1)
    st.write("")
    with st.expander("Weitere Auswertungen: Ziele im Detail, Fallbelastung, Regeländerung 2027, alle Fälle"):
        mehr = st.segmented_control("Auswertung", ["Ziele im Detail", "Fallbelastung", "Regeländerung 2027", "Alle Fälle"],
                                    key="le_mehr")
        mehr_box = st.container()

    # ---------------- Überblick ----------------
    with haupt[1]:
        ui.kacheln([
            ("Personen", len(m), f"in {m['dossier'].nunique()} Haushalten", None),
            ("Ziele erreicht", int((staende == "Erreicht").sum().sum()), "über alle drei Ziele", "Erreicht"),
            ("Ziele auf Kurs", int((staende == "Auf Kurs").sum().sum()), "Frist gut erreichbar", "Auf Kurs"),
            ("Ziele gefährdet", int((staende == "Gefährdet").sum().sum()), "jetzt handeln", "Gefährdet"),
            ("Erreicht, nicht erfasst", nicht_erfasst, "Abgeltung noch offen", None),
        ])
        for titel, ser, text in [
            ("Ziel 1: Sprache A1", z1["stand"], "Personen ab 16, Frist 3 Jahre ab Einreise"),
            ("Ziel 2: Arbeit oder Ausbildung", z2["stand"], "Personen ab 16, Frist Zuständigkeitsende"),
            ("Ziel 3: 12 Monate ohne Sozialhilfe", z3["stand"], "Pro Haushalt, Frist Zuständigkeitsende"),
        ]:
            n = int((ser != "Nicht anwendbar").sum())
            erreicht = int((ser == "Erreicht").sum())
            ui.abschnitt(titel, f"{text}. {erreicht} von {n} erreicht ({erreicht / max(1, n):.0%}).")
            st.plotly_chart(ui.verteilung(ser), width="stretch", config=CFG, key=f"vt_{titel}")
        ui.abschnitt("Wo braucht das Team Unterstützung?",
                     "Ziele pro Fallführung, über alle drei Ziele. Auf einen Balken klicken zeigt die gefährdeten Fälle.")
        lang = pd.concat([m[["sozialarbeit", f"stand{i}"]].rename(columns={f"stand{i}": "stand"}) for i in (1, 2, 3)], ignore_index=True)
        lang = lang[lang["stand"] != "Nicht anwendbar"]
        team = pd.crosstab(lang["sozialarbeit"], lang["stand"]).reindex(columns=STAENDE, fill_value=0)
        team = team.assign(_rot=team["Gefährdet"]).sort_values("_rot", ascending=False).drop(columns="_rot")
        team = team.reset_index().rename(columns={"sozialarbeit": "Fallführung"})
        fig = ui.gestapelt(team, "Fallführung", STAENDE, hoehe=80 + 38 * len(team))
        ev = st.plotly_chart(fig, width="stretch", config=CFG, on_select="rerun", selection_mode="points", key="le_team")
        punkte = ev.selection.points if ev and ev.selection else []
        if punkte:
            sa = punkte[0].get("y")
            ms = m[m["sozialarbeit"] == sa]
            li = aufgaben(ms, z1[z1["sozialarbeit"] == sa], z2[z2["sozialarbeit"] == sa], z3[z3["sozialarbeit"] == sa])
            ui.abschnitt(f"Gefährdet bei {sa} ({len(li['rot'])})", "«Öffnen» zeigt die Fallakte")
            info = ms.set_index("zemis")
            for n, e in enumerate(li["rot"][:15]):
                wl_zeile(ctx, e, info, "rot", 1000 + n)
            if not li["rot"]:
                st.success("Keine gefährdeten Ziele.")
        ui.abschnitt("A1 erreicht pro Monat", "Letzte 24 Monate, nur in Frist")
        v = abgeltung.verlauf(z1, stichtag)
        fig = ui.balken_einfach(v["Monat"], v["A1 erreicht"], hoehe=240, farbe=ui.FARBE["Erreicht"])
        fig.update_xaxes(tickformat="%m.%y", dtick="M3")
        st.plotly_chart(fig, width="stretch", config=CFG)

    # ---------------- Ziele im Detail ----------------
    if mehr == "Ziele im Detail":
        with mehr_box:
            wahl = st.segmented_control("Ziel", list(ZIEL.values()), default=ZIEL[1], key="le_ziel")
            quote = st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)
            if wahl == ZIEL[3]:
                df, einheit = z3, "Haushalte"
            elif wahl == ZIEL[2]:
                df, einheit = z2, "Personen"
            else:
                df, einheit = z1, "Personen"
            sc = df[df["stand"] != "Nicht anwendbar"]
            c = sc["stand"].value_counts()
            ui.kacheln([
                (f"{einheit} mit Ziel", len(sc), f"von {len(df)}", None),
                ("Erreicht", int(c.get("Erreicht", 0)), f"{c.get('Erreicht', 0) / max(1, len(sc)):.0%}", "Erreicht"),
                ("Auf Kurs", int(c.get("Auf Kurs", 0)), "", "Auf Kurs"),
                ("Gefährdet", int(c.get("Gefährdet", 0)), "", "Gefährdet"),
                ("Frist verpasst", int(c.get("Frist verpasst", 0)), "", "Frist verpasst"),
            ])
            t_sa = totale(df, "sozialarbeit")
            ui.abschnitt("Stand pro Fallführung", f"Anzahl {einheit}. Für die Zahl über einen Balken fahren.")
            ohne = t_sa[t_sa["Fallführung"] != "Total"].sort_values("Im Scope", ascending=False)
            st.plotly_chart(ui.gestapelt(ohne, "Fallführung", STAENDE, hoehe=80 + 38 * len(ohne)), width="stretch", config=CFG)
            st.dataframe(t_sa, hide_index=True, width="stretch", column_config={"Quote erreicht": quote})
            if "einreisejahr" in df.columns:
                t_j = totale(sc, "einreisejahr")
                ui.abschnitt("Stand pro Einreisejahr")
                oj = t_j[t_j["Einreisejahr"] != "Total"]
                st.plotly_chart(ui.gestapelt(oj, "Einreisejahr", STAENDE, horizontal=False, hoehe=340), width="stretch", config=CFG)
                st.dataframe(t_j, hide_index=True, width="stretch", column_config={"Quote erreicht": quote})
            ui.abschnitt(f"Alle {einheit}", "Die dringendsten zuerst")
            if wahl == ZIEL[1]:
                ui.tabelle(fuer_anzeige(z1), key="le_t1")
            elif wahl == ZIEL[2]:
                ui.tabelle(anzeige_z2(z2.sort_values("stand", key=lambda s: s.map({x: i for i, x in enumerate(REIHENFOLGE)}))), key="le_t2")
            else:
                ui.tabelle(anzeige_z3(z3.sort_values("stand", key=lambda s: s.map({x: i for i, x in enumerate(REIHENFOLGE)}))), key="le_t3")

    # ---------------- Erfolgsfaktoren (Stufe 2) ----------------
    with haupt[3]:
        mk = analysen.merkmale(d, z1)
        gesamt, tabellen, rang = analysen.erfolgsfaktoren(mk)
        ui.abschnitt("Was haben die Personen gemeinsam, die A1 in der Frist erreicht haben?",
                     f"Basis: {len(mk)} Personen mit abgeschlossenem Ziel 1 (erreicht oder Frist vorbei). "
                     f"Insgesamt erreicht: {gesamt:.0%}. Gruppen unter {analysen.MIN_GRUPPE} Personen werden nicht gezeigt.")
        if len(mk) < 2 * analysen.MIN_GRUPPE or rang.empty:
            st.info("Zu wenige abgeschlossene Fälle für eine Auswertung mit diesem Filter.")
        else:
            l, r = st.columns([1, 1.4], gap="large")
            with l:
                ui.abschnitt("Wo ist der Unterschied am grössten?", "Abstand zwischen bester und schwächster Gruppe")
                fig = ui.balken_einfach(rang["Merkmal"], rang["Spannweite"], hoehe=60 + 36 * len(rang),
                                        horizontal=True, prozent=True)
                fig.update_xaxes(range=[0, max(0.1, rang["Spannweite"].max() * 1.1)])
                st.plotly_chart(fig, width="stretch", config=CFG)
            with r:
                wahl_m = st.selectbox("Merkmal", list(rang["Merkmal"]), key="le_merkmal")
                st.plotly_chart(gruppen_chart(tabellen[wahl_m], gesamt), width="stretch", config=CFG)
                st.dataframe(tabellen[wahl_m], hide_index=True, width="stretch", column_config={
                    "Quote": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
                    "Differenz": st.column_config.NumberColumn(format="percent")})
            st.caption("Merkmale hängen zusammen (z.B. Muttersprache und Alphabetisierung). Die Auswertung zeigt, "
                       "wo Unterschiede liegen, nicht warum. Kein Wert pro Person.")
        with st.expander("Situationsanalyse einbeziehen"):
            st.markdown("Die Situationsanalyse ist Freitext. Eine **regelbasierte Extraktion** liest pro Haushalt "
                        "nur diese Felder aus: **Alphabetisierung, Schuljahre, Berufserfahrung**. "
                        "**Gesundheitsangaben werden nicht gelesen.** Die Verarbeitung bleibt lokal – kein Text "
                        "verlässt das Netz der Stadt. Die erkannten Felder kommen unten als zusätzliche Merkmale in "
                        "die Gruppenauswertung.")

            sa_ordner = situationsanalyse.extrahiere_ordner(daten.DEMO / "situationsanalysen") if daten.ist_demo() else situationsanalyse._frame([])
            if daten.ist_demo() and not sa_ordner.empty:
                st.caption(f"{len(sa_ordner)} Berichte aus `daten/demo/situationsanalysen` gelesen (synthetisch).")
            hochgeladen = st.file_uploader("Weitere Situationsanalysen (.txt)", type=["txt"], accept_multiple_files=True, key="sa_upload")
            sa_up = situationsanalyse.extrahiere_dateien([(f.name, f.getvalue().decode("utf-8", "ignore")) for f in hochgeladen or []])
            sa = pd.concat([sa_ordner, sa_up], ignore_index=True)
            if not sa.empty:
                sa = sa.drop_duplicates("zemis", keep="last").reset_index(drop=True)

            if sa.empty:
                st.info("Noch keine Situationsanalyse-Berichte. Lege `.txt`-Dateien in `daten/demo/situationsanalysen` "
                        "oder lade oben welche hoch. (Demodaten erzeugen: `python tools/synthetische_daten.py`.)")
            else:
                st.markdown("**Ausgelesene Felder**")
                st.dataframe(sa.rename(columns={"zemis": "Zemis-Nr.", "datei": "Datei", "alphabetisiert": "Alphabetisiert",
                                                "schuljahre": "Schuljahre", "berufserfahrung_jahre": "Berufserfahrung (Jahre)"}),
                             hide_index=True, width="stretch")
                mk_sa, namen = situationsanalyse.als_merkmale(mk, sa)
                treffer = int(mk_sa["zemis"].astype("string").isin(sa["zemis"]).sum())
                if not namen or treffer < analysen.MIN_GRUPPE or len(mk_sa) < 2 * analysen.MIN_GRUPPE:
                    st.caption(f"{treffer} der ausgewerteten Personen haben einen Bericht – noch zu wenige für eine Gruppenauswertung.")
                else:
                    _, tab_sa, _ = analysen.erfolgsfaktoren(mk_sa, extra=namen)
                    ui.abschnitt("Situationsanalyse als Erfolgsfaktoren", f"{treffer} Personen mit Bericht. Nur Gruppen ab {analysen.MIN_GRUPPE} Personen.")
                    wahl_sa = st.selectbox("Merkmal aus der Situationsanalyse", namen, key="le_merkmal_sa")
                    st.plotly_chart(gruppen_chart(tab_sa[wahl_sa], gesamt), width="stretch", config=CFG)
                    st.dataframe(tab_sa[wahl_sa], hide_index=True, width="stretch", column_config={
                        "Quote": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
                        "Differenz": st.column_config.NumberColumn(format="percent")})
                    st.caption("Gleiche Schutzregel wie oben: nur Gruppen, nie ein Wert pro Person. Gesundheit wird nicht gelesen.")

    # ---------------- Fallbelastung ----------------
    if mehr == "Fallbelastung":
        with mehr_box:
            fb = analysen.fallbelastung(z1, m)
            ui.abschnitt("Fallbelastung pro Fallführung", "Personen und Haushalte, offene Ziele und Personen mit roter Ampel")
            fig = go.Figure()
            fig.add_bar(y=fb["Fallführung"], x=fb["Personen"] - fb["Mit roter Ampel"], orientation="h", name="ohne rote Ampel",
                        marker=dict(color="#9fb3c4", line=dict(color="#fff", width=2)), hovertemplate="%{y}: %{x}<extra>ohne rot</extra>")
            fig.add_bar(y=fb["Fallführung"], x=fb["Mit roter Ampel"], orientation="h", name="mit roter Ampel",
                        marker=dict(color=ui.FARBE["Gefährdet"], line=dict(color="#fff", width=2)), hovertemplate="%{y}: %{x}<extra>rot</extra>")
            fig = ui._layout(fig, 80 + 38 * len(fb))
            fig.update_yaxes(autorange="reversed", type="category")
            st.plotly_chart(fig, width="stretch", config=CFG)
            st.dataframe(fb, hide_index=True, width="stretch", column_config={
                "Anteil rot": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1)})

    # ---------------- Abgeltung ----------------
    with haupt[2]:
        offen = []
        for _, r in z1[(z1["stand"] == "Erreicht") & (~z1["gemeldet"])].iterrows():
            offen.append({"Ziel": ZIEL[1], "Wer": f"Klient:in {r['klientennr']}", "Fallführung": r["sozialarbeit"], "Grund": r["grund"]})
        for _, r in z2[z2["schritt"] == "Zielerreichung erfassen"].iterrows():
            offen.append({"Ziel": ZIEL[2], "Wer": f"Klient:in {r['klientennr']}", "Fallführung": r["sozialarbeit"], "Grund": r["grund"]})
        for _, r in z3[z3["schritt"] == "Zielerreichung erfassen"].iterrows():
            offen.append({"Ziel": ZIEL[3], "Wer": f"Haushalt {r['dossier']}", "Fallführung": r["sozialarbeit"], "Grund": r["grund"]})
        offen = pd.DataFrame(offen, columns=["Ziel", "Wer", "Fallführung", "Grund"])
        ui.kacheln([
            ("Erreicht, nicht erfasst", len(offen), "Abgeltung noch offen", None),
            (ZIEL[1], int((offen["Ziel"] == ZIEL[1]).sum()), "Personen", None),
            (ZIEL[2], int((offen["Ziel"] == ZIEL[2]).sum()), "Personen", None),
            (ZIEL[3], int((offen["Ziel"] == ZIEL[3]).sum()), "Haushalte", None),
        ])
        ui.abschnitt("Ziel erreicht, aber nicht in der Integrationszielerreichung erfasst",
                     "Diese Fälle sind erreicht. Sobald sie erfasst sind, zählen sie für die Abgeltung.")
        if offen.empty:
            st.success("Alle erreichten Ziele sind erfasst.")
        else:
            st.dataframe(offen, hide_index=True, width="stretch", height=min(420, 38 * (len(offen) + 1)))
        ui.abschnitt("Übersicht pro Ziel: erfasst, offen, noch möglich, verloren",
                     "Abgeltung gibt es nur, wenn ein Ziel innerhalb der Frist erreicht ist.")
        ze = d["zielerreichung"]
        jahr = pd.Timestamp(stichtag).year
        betraege = {}
        cols = st.columns(3)
        for i, sp in zip((1, 2, 3), cols):
            betraege[i] = sp.number_input(f"Betrag pro {ZIEL[i]} in CHF", min_value=0, step=100, value=0, key=f"chf{i}",
                                          help="Optional, aus dem Leistungsvertrag. Wird nicht gespeichert.")
        muster = {1: "sprache", 2: "erwerb|ausbildung|arbeit", 3: "ablösung|sozialhilfe"}
        zeilen = []
        for i, df in ((1, z1), (2, z2), (3, z3)):
            erfasst = int((ze["art"].astype("string").str.lower().str.contains(muster[i], na=False)
                           & (ze["datum"].dt.year == jahr)).sum())
            offen = int(((df["stand"] == "Erreicht") & ~df["gemeldet"]).sum()) if i == 1 else int((df["schritt"] == "Zielerreichung erfassen").sum())
            frist_col = "tage_bis_frist" if i == 1 else "tage_bis_ende"
            moeglich = df[df["stand"].isin(["Auf Kurs", "Gefährdet"])]
            m12 = int((moeglich[frist_col] <= 365).sum())
            verloren = int((df["stand"] == "Frist verpasst").sum())
            b = betraege[i]
            zeilen.append({"Ziel": ZIEL[i], f"Erfasst {jahr}": erfasst, "Erreicht, nicht erfasst": offen,
                           "Möglich in 12 Mt.": m12, "Möglich total": len(moeglich), "Verloren": verloren,
                           "CHF nicht erfasst": offen * b if b else None, "CHF möglich in 12 Mt.": m12 * b if b else None})
        tab = pd.DataFrame(zeilen)
        st.dataframe(tab, hide_index=True, width="stretch", column_config={
            "CHF nicht erfasst": st.column_config.NumberColumn(format="CHF %d"),
            "CHF möglich in 12 Mt.": st.column_config.NumberColumn(format="CHF %d")})
        st.caption("«Verloren»: Frist nicht mehr erreichbar. «Möglich»: auf Kurs oder gefährdet.")

    # ---------------- Regeländerung 2027 ----------------
    if mehr == "Regeländerung 2027":
        with mehr_box:
            sz = analysen.szenario_2027(d, stichtag, ctx["z2"], ctx["z3"])
            p = sz["personen"][sz["personen"]["zemis"].isin(set(z1["zemis"]))]
            ui.abschnitt("Was passiert, wenn die Zuständigkeit für VA / F-FL ab 2027 nach 5 statt 7 Jahren endet?",
                         "Annahme: neues Ende = Einreise + 5 Jahre, frühestens 01.01.2027. Ziel 1 ändert sich nicht (Frist 3 Jahre).")
            v2, v3 = sz["z2_vergleich"], sz["z3_vergleich"]
            kippt2 = int(v2.loc["Auf Kurs", "Gefährdet"]) if "Auf Kurs" in v2.index and "Gefährdet" in v2.columns else 0
            verl3 = int(v3.drop(index="Frist verpasst", errors="ignore").get("Frist verpasst", pd.Series(dtype=int)).sum())
            ui.kacheln([
                ("Früheres Zuständigkeitsende", len(p), "aktuelle Personen", None),
                ("Im Schnitt früher", f"{p['Monate früher'].mean():.0f} Mt." if len(p) else "–", "weniger Zeit für Ziel 2 und 3", None),
                ("Ziel 2: neu gefährdet", kippt2, "von «auf Kurs» zu «gefährdet»", "Gefährdet"),
                ("Ziel 3: neu verloren", verl3, "Haushalte, Frist nicht mehr erreichbar", "Frist verpasst"),
            ])
            a, b = st.columns(2)
            a.markdown("**Ziel 2: heute (Zeilen) und ab 2027 (Spalten)**")
            a.dataframe(v2, width="stretch")
            b.markdown("**Ziel 3: heute (Zeilen) und ab 2027 (Spalten)**")
            b.dataframe(v3, width="stretch")
            ui.abschnitt("Betroffene Personen", "Diese Fälle jetzt priorisieren")
            st.dataframe(p.rename(columns={"klientennr": "Klientennummer", "zemis": "Zemis-Nr.", "dossier": "Dossier-Nr.",
                                           "sozialarbeit": "Fallführung", "status_aktuell": "Verfahrensstand",
                                           "zust_ende": "Ende heute", "zust_ende_2027": "Ende ab 2027"}),
                         hide_index=True, width="stretch", column_config={
                             "Ende heute": st.column_config.DateColumn(format="DD.MM.YYYY"),
                             "Ende ab 2027": st.column_config.DateColumn(format="DD.MM.YYYY")})

    # ---------------- Alle Fälle ----------------
    if mehr == "Alle Fälle":
        with mehr_box:
            ui.abschnitt("Ampel pro Person und Ziel", "Die dringendsten zuerst. Zeile anklicken für Details.")
            sel = ui.tabelle(anzeige_matrix(m), key="le_matrix")
            if sel is not None:
                if st.button(f"Fallakte von Klient:in {sel['Klientennummer']} öffnen", key="le_akte_btn",
                         type="primary", icon=":material/folder_open:"):
                    fallakte.oeffnen(ctx, sel["Zemis-Nr."])

    st.divider()
    mk = analysen.merkmale(d, z1)
    _, tabellen, rang = analysen.erfolgsfaktoren(mk)
    erfolg = pd.concat([t.assign(Merkmal=k) for k, t in tabellen.items()], ignore_index=True) if tabellen else pd.DataFrame()
    ui.excel_knopf("Bericht als Excel herunterladen", {
        "Ampel pro Person": anzeige_matrix(m),
        "Ziel 1 pro Fallführung": totale(z1, "sozialarbeit"),
        "Ziel 1 pro Einreisejahr": totale(z1[z1["im_scope"]], "einreisejahr"),
        "Ziel 2 pro Fallführung": totale(z2, "sozialarbeit"),
        "Ziel 3 pro Fallführung": totale(z3, "sozialarbeit"),
        "Erfolgsfaktoren Ziel 1": erfolg,
        "Fallbelastung": analysen.fallbelastung(z1, m),
        "Datenqualität": ctx["dq"],
    }, {"Bericht": "Integrations-Cockpit, Ziele 1 bis 3", "Stichtag": f"{stichtag:%d.%m.%Y}",
        "Datenquelle": ctx["quelle"], "Filter": f"{len(m)} Personen",
        "Hinweis": f"Gruppenauswertung. Kein Score pro Person. Gruppen unter {analysen.MIN_GRUPPE} Personen ausgeblendet."},
        f"Cockpit_Leitung_{stichtag:%Y%m%d}.xlsx")
