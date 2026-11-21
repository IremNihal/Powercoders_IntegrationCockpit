"""Gemeinsame UI-Bausteine: Stil, Kennzahl-Kacheln, Tabellen, Diagramme."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cockpit.regeln import AMPEL, fuer_anzeige
from cockpit.export import excel

# Statusfarben (Ampel) – immer zusammen mit Symbol und Text, nie Farbe allein
FARBE = {
    "Erreicht": "#0ca30c",
    "Erreicht nach Frist": "#8fcf8f",
    "Auf Kurs": "#fab219",
    "Gefährdet": "#d03b3b",
    "Frist verpasst": "#5f5e58",
    "Nicht anwendbar": "#d6d5ce",
}
# Grundpalette: Tinte, Schiefer, Nebel, Papier, Linie, Aare (Akzent)
TINTE, TINTE_2, RASTER, ACHSE = "#15202b", "#5b6672", "#e3e8ee", "#c5cdd6"
AARE, AARE_HELL = "#0f6e73", "#e2f0f0"
SCHRIFT = "Atkinson, sans-serif"

KLASSE = {"Gefährdet": "rot", "Auf Kurs": "gelb", "Erreicht": "gruen", "Frist verpasst": "grau"}


def stil():
    st.markdown("""
    <style>
      #MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {display:none;}
      header[data-testid="stHeader"] {background: transparent;}
      .block-container {padding-top: 1.2rem; max-width: 1280px;}
      * {font-variant-numeric: tabular-nums;}

      /* Kopfband */
      .band {background:#15202b; color:#fff; border-radius:14px; padding:22px 28px 20px;
             display:flex; justify-content:space-between; align-items:flex-end; gap:24px;
             box-shadow: inset 0 -4px 0 #0f6e73; margin-bottom:18px;}
      .band h1 {color:#fff !important; font-size:1.65rem !important; font-weight:700; margin:0 !important; padding:0 !important;
                letter-spacing:-0.01em; line-height:1.2;}
      .band .unter {color:#b9c4cf; margin-top:4px; font-size:.98rem;}
      .band .rechts {text-align:right; color:#b9c4cf; font-size:.9rem; white-space:nowrap;}
      .band .rechts b {color:#fff; font-size:1.05rem;}
      .demo-chip {display:inline-block; background:#fab219; color:#15202b; font-weight:700; border-radius:6px;
                  padding:2px 8px; font-size:.78rem; margin-bottom:6px;}

      /* Kennzahlen: eine Leiste statt vieler Karten */
      .leiste {display:flex; background:#fff; border:1px solid #d5dbe2; border-radius:12px; margin:4px 0 22px;}
      .leiste .zelle {flex:1; padding:16px 20px; border-left:1px solid #e3e8ee; min-width:0;}
      .leiste .zelle:first-child {border-left:none;}
      .leiste .label {color:#5b6672; font-size:.88rem; display:flex; align-items:center; gap:7px;}
      .leiste .wert {font-size:2.3rem; font-weight:700; color:#15202b; line-height:1.15; margin-top:2px;}
      .leiste .zusatz {color:#5b6672; font-size:.82rem;}
      .punkt {display:inline-block; width:10px; height:10px; border-radius:50%; flex:none;}

      /* Abschnitte */
      .abschnitt {margin: 14px 0 8px;}
      .abschnitt .t {font-weight:700; font-size:1.08rem; color:#15202b;}
      .abschnitt .d {color:#5b6672; font-size:.9rem;}

      /* Tabs als Schalter */
      .stTabs [role="tablist"] {gap:4px; background:#fff; border:1px solid #d5dbe2; border-radius:12px; padding:5px;
                                width:fit-content; max-width:100%; flex-wrap:wrap; border-bottom:1px solid #d5dbe2;}
      .stTabs [data-testid="stTab"] {border-radius:8px; padding:7px 14px; height:auto; margin:0;}
      .stTabs [data-testid="stTab"] p {color:#5b6672; font-size:.95rem;}
      .stTabs [data-testid="stTab"]:hover {background:#eef1f5;}
      .stTabs [data-testid="stTab"][aria-selected="true"] {background:#e2f0f0;}
      .stTabs [data-testid="stTab"][aria-selected="true"] p {color:#0f6e73; font-weight:700;}
      .stTabs .react-aria-SelectionIndicator {display:none;}
      .stTabs [data-testid="stTab"]:focus-visible {outline:2px solid #0f6e73; outline-offset:2px;}

      /* Arbeitsliste */
      .liste {background:#fff; border:1px solid #d5dbe2; border-radius:12px; overflow:hidden; margin-bottom:18px;}
      .liste .kopf {padding:12px 18px; border-bottom:1px solid #e3e8ee; display:flex; justify-content:space-between; align-items:baseline;}
      .liste .kopf .t {font-weight:700; color:#15202b;}
      .liste .kopf .d {color:#5b6672; font-size:.88rem;}
      .zeile {display:grid; grid-template-columns: 6px 1.1fr 1.6fr 1.1fr; gap:0 16px; align-items:center;
              border-bottom:1px solid #eef1f5; padding-right:18px; min-height:62px;}
      .zeile:last-child {border-bottom:none;}
      .zeile .streifen {align-self:stretch;}
      .zeile .wer {font-weight:700; color:#15202b; padding:10px 0;}
      .zeile .wer small {display:block; font-weight:400; color:#5b6672;}
      .zeile .warum {color:#2d3a46; font-size:.93rem;}
      .zeile .schritt {justify-self:start; background:#e2f0f0; color:#0f6e73; font-weight:700; font-size:.86rem;
                       border-radius:999px; padding:5px 12px;}
      .rot .streifen, .streifen.rot {background:#d03b3b;} .gelb .streifen, .streifen.gelb {background:#fab219;}
      .gruen .streifen, .streifen.gruen {background:#0ca30c;} .streifen.grau {background:#5f5e58;}

      /* Handlungsfelder (Leitung) */
      .felder {display:flex; background:#fff; border:1px solid #d5dbe2; border-radius:12px; margin-bottom:22px;}
      .feld {flex:1; padding:18px 20px; border-left:1px solid #e3e8ee; display:flex; gap:16px;}
      .feld:first-child {border-left:none;}
      .feld .zahl {font-size:2.3rem; font-weight:700; line-height:1; min-width:56px;}
      .feld .titel {font-weight:700; color:#15202b; margin-bottom:3px;}
      .feld .text {color:#5b6672; font-size:.88rem;}
      .feld.rot .zahl {color:#b42f2f;} .feld.gelb .zahl {color:#9a6a00;} .feld.gruen .zahl {color:#0a7d0a;}

      /* Sidebar */
      section[data-testid="stSidebar"] {border-right:1px solid #d5dbe2;}
      .wer-bin-ich {padding:4px 0 10px;}
      .wer-bin-ich .n {font-weight:700; font-size:1.05rem;}
      .wer-bin-ich .r {display:inline-block; margin-top:4px; background:#e2f0f0; color:#0f6e73; font-weight:700;
                       font-size:.8rem; border-radius:999px; padding:2px 10px;}
      .wer-bin-ich .h {color:#5b6672; font-size:.85rem; margin-top:8px;}

      /* Anmeldung */
      .login-links {background:#15202b; color:#dfe6ec; border-radius:16px; padding:36px 34px; height:100%;
                    box-shadow: inset 0 -5px 0 #0f6e73;}
      .login-links h1 {color:#fff !important; font-size:2rem !important; line-height:1.15; padding:0 !important; margin:0 0 14px !important;}
      .login-links p {color:#b9c4cf; font-size:1rem; line-height:1.55; max-width:34ch;}
      .login-links .fakt {margin-top:22px; border-top:1px solid #2c3a48; padding-top:14px; font-size:.9rem; color:#b9c4cf;}

      /* Arbeitsliste mit Zeilen (Container mit key wl_<klasse>_<n>) */
      [class*="st-key-wl_"] {background:#fff; border:1px solid #d5dbe2 !important; border-left:6px solid #9aa6b2 !important;
                             border-radius:10px; padding:10px 14px 10px 16px !important; margin-bottom:-6px;}
      [class*="st-key-wl_rot_"] {border-left-color:#d03b3b !important;}
      [class*="st-key-wl_gelb_"] {border-left-color:#fab219 !important;}
      [class*="st-key-wl_gruen_"] {border-left-color:#0ca30c !important;}
      [class*="st-key-wl_"]:hover {box-shadow: 0 2px 10px rgba(21,32,43,.08);}
      .wl-wer {font-weight:700; color:#15202b; line-height:1.25;}
      .wl-wer small {display:block; font-weight:400; color:#5b6672; font-size:.84rem;}
      .wl-ziel {display:inline-block; font-size:.76rem; font-weight:700; color:#15202b; background:#eef1f5;
                border-radius:6px; padding:1px 7px; margin-bottom:3px;}
      .wl-grund {color:#2d3a46; font-size:.92rem; line-height:1.35;}
      .wl-frist {display:inline-block; font-size:.76rem; font-weight:700; color:#fff; background:#d03b3b;
                 border-radius:6px; padding:1px 7px; margin-left:6px;}
      .wl-schritt {display:inline-block; background:#e2f0f0; color:#0f6e73; font-weight:700; font-size:.86rem;
                   border-radius:999px; padding:5px 12px; line-height:1.3;}

      /* Fallakte */
      .akte-kopf {background:#15202b; color:#fff; border-radius:12px; padding:16px 20px; margin-bottom:14px;
                  box-shadow: inset 0 -4px 0 #0f6e73;}
      .akte-titel {font-size:1.45rem; font-weight:700;}
      .akte-chips {display:flex; flex-wrap:wrap; gap:6px; margin-top:8px;}
      .akte-chips span {background:rgba(255,255,255,.1); color:#dfe6ec; border-radius:999px; padding:3px 10px; font-size:.85rem;}
      .ziel-reihe {display:grid; grid-template-columns:repeat(3, 1fr); gap:12px; margin-bottom:6px;}
      .ziel-karte {background:#fff; border:1px solid #d5dbe2; border-top:5px solid #d6d5ce; border-radius:10px; padding:12px 14px;}
      .ziel-name {color:#5b6672; font-size:.82rem;}
      .ziel-stand {font-weight:700; font-size:1.05rem; margin:2px 0 4px;}
      .ziel-grund {color:#2d3a46; font-size:.88rem; line-height:1.35;}
      .ziel-schritt {display:inline-block; margin-top:8px; background:#e2f0f0; color:#0f6e73; font-weight:700; font-size:.82rem;
                     border-radius:999px; padding:4px 10px;}
      div[role="dialog"] {background:#eef1f5;}

      @media (max-width: 900px) {
        .ziel-reihe {grid-template-columns:1fr;}
        .leiste, .felder {flex-wrap:wrap;} .leiste .zelle, .feld {flex:1 1 45%; border-left:none; border-top:1px solid #e3e8ee;}
        .zeile {grid-template-columns: 6px 1fr; } .zeile .warum, .zeile .schritt {grid-column:2; margin-bottom:8px;}
        .band {flex-direction:column; align-items:flex-start;} .band .rechts {text-align:left;}
      }
    </style>""", unsafe_allow_html=True)


def band(titel: str, unter: str, rechts_oben: str, rechts: str, demo: bool = False):
    chip = '<div class="demo-chip">Demodaten, alle Personen erfunden</div><br>' if demo else ""
    st.markdown(f'<div class="band"><div><h1>{titel}</h1><div class="unter">{unter}</div></div>'
                f'<div class="rechts">{chip}{rechts_oben}<br><b>{rechts}</b></div></div>', unsafe_allow_html=True)


def kopf(titel: str, untertitel: str):
    """Kopfband mit Stichtag rechts (Stichtag und Demo-Hinweis kommen aus dem Session-State)."""
    stt = st.session_state.get("_stichtag")
    band(titel, untertitel, "Stand", f"{stt:%d.%m.%Y}" if stt else "", st.session_state.get("_demo", False))


def abschnitt(titel: str, text: str = ""):
    st.markdown(f'<div class="abschnitt"><div class="t">{titel}</div>'
                + (f'<div class="d">{text}</div>' if text else "") + '</div>', unsafe_allow_html=True)


def kacheln(werte: list):
    """Kennzahlen als eine Leiste. werte: [(label, wert, zusatz, stand_oder_None)]"""
    zellen = []
    for label, wert, zusatz, stand in werte:
        punkt = f'<span class="punkt" style="background:{FARBE[stand]}"></span>' if stand else ""
        zellen.append(f'<div class="zelle"><div class="label">{punkt}{label}</div>'
                      f'<div class="wert">{wert}</div><div class="zusatz">{zusatz}</div></div>')
    st.markdown(f'<div class="leiste">{"".join(zellen)}</div>', unsafe_allow_html=True)


def felder(eintraege: list):
    """Handlungsfelder: [(titel, zahl, text, klasse)]"""
    html = "".join(f'<div class="feld {k}"><div class="zahl">{z}</div><div><div class="titel">{t}</div>'
                   f'<div class="text">{x}</div></div></div>' for t, z, x, k in eintraege)
    st.markdown(f'<div class="felder">{html}</div>', unsafe_allow_html=True)


def arbeitsliste(titel: str, text: str, zeilen: list, klasse: str):
    """zeilen: [(wer, wer_klein, warum, schritt)]"""
    rows = "".join(f'<div class="zeile {klasse}"><div class="streifen"></div><div class="wer">{w}<small>{wk}</small></div>'
                   f'<div class="warum">{wa}</div>' + (f'<div class="schritt">{s}</div>' if s else '<div></div>') + '</div>'
                   for w, wk, wa, s in zeilen)
    st.markdown(f'<div class="liste {klasse}"><div class="kopf"><span class="t">{titel}</span>'
                f'<span class="d">{text}</span></div>{rows}</div>', unsafe_allow_html=True)


def zahlen(z1: pd.DataFrame) -> dict:
    sc = z1[z1["im_scope"]]
    n = len(sc)
    c = sc["stand"].value_counts()
    return {
        "scope": n, "erreicht": int(c.get("Erreicht", 0)), "auf_kurs": int(c.get("Auf Kurs", 0)),
        "gefaehrdet": int(c.get("Gefährdet", 0)), "verpasst": int(c.get("Frist verpasst", 0)),
        "nach_frist": int(c.get("Erreicht nach Frist", 0)),
        "quote": (c.get("Erreicht", 0) / n) if n else 0,
        "nicht_gemeldet": int(((sc["stand"] == "Erreicht") & ~sc["gemeldet"]).sum()),
        "quick_win": int(sc["naechster_schritt"].eq("Zur A1-Prüfung anmelden").sum()),
    }


SPALTEN_CFG = {
    "Einreise": st.column_config.DateColumn(format="DD.MM.YYYY"),
    "Frist A1": st.column_config.DateColumn(format="DD.MM.YYYY"),
    "A1 erreicht am": st.column_config.DateColumn(format="DD.MM.YYYY"),
    "Deutschkurs läuft": st.column_config.CheckboxColumn(),
    "Als Ziel gemeldet": st.column_config.CheckboxColumn(),
    "Tage bis Frist": st.column_config.NumberColumn(format="%d"),
    "Grund": st.column_config.TextColumn(width="large"),
}


def fallliste(z1: pd.DataFrame, key: str, spalten=None):
    """Tabelle mit Auswahl; gibt die gewählte Zemis-Nr. zurück."""
    df = fuer_anzeige(z1)
    if spalten:
        df = df[spalten]
    ev = st.dataframe(df, hide_index=True, width="stretch", column_config=SPALTEN_CFG,
                      on_select="rerun", selection_mode="single-row", key=key, height=420)
    rows = ev.selection.rows if ev and ev.selection else []
    return df.iloc[rows[0]]["Zemis-Nr."] if rows else None


def person_detail(d, z1, zemis):
    r = z1[z1["zemis"] == zemis].iloc[0]
    st.markdown(f"#### {AMPEL[r['stand']]} Klient:in {r['klientennr']}, {r['status']}, {int(r['alter'])} Jahre")
    a, b, c = st.columns(3)
    a.markdown(f"**Einreise** {r['einreise']:%d.%m.%Y}" if pd.notna(r["einreise"]) else "**Einreise** –")
    b.markdown(f"**Frist A1** {r['frist']:%d.%m.%Y}" if pd.notna(r["frist"]) else "**Frist A1** –")
    c.markdown(f"**Fallführung** {r['sozialarbeit']}")
    st.markdown(f"**Warum:** {r['grund']}" + (f"  \n**Nächster Schritt:** {r['naechster_schritt']}" if r["naechster_schritt"] else ""))
    s = d["sprache"][d["sprache"]["zemis"] == zemis][["datum", "sprache", "niveau", "art", "bemerkungen"]]
    f = d["foerderung"][d["foerderung"]["zemis"] == zemis][["start", "abschluss", "art", "bezeichnung", "stunden"]]
    l, rr = st.columns(2)
    l.caption("Sprachstand")
    l.dataframe(s.sort_values("datum").rename(columns={"datum": "Datum", "sprache": "Sprache", "niveau": "Niveau",
                "art": "Nachweis", "bemerkungen": "Bemerkungen"}), hide_index=True, width="stretch",
                column_config={"Datum": st.column_config.DateColumn(format="DD.MM.YYYY")})
    rr.caption("Kurse und Ausbildung")
    rr.dataframe(f.sort_values("start").rename(columns={"start": "Start", "abschluss": "Abschluss", "art": "Art",
                 "bezeichnung": "Bezeichnung", "stunden": "Std./Woche"}), hide_index=True, width="stretch",
                 column_config={"Start": st.column_config.DateColumn(format="DD.MM.YYYY"),
                                "Abschluss": st.column_config.DateColumn(format="DD.MM.YYYY")})


def _layout(fig, hoehe):
    fig.update_layout(
        height=hoehe, margin=dict(l=8, r=8, t=8, b=8), plot_bgcolor="#ffffff", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TINTE, size=13, family=SCHRIFT), bargap=0.35, barmode="stack",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None, traceorder="normal", font=dict(color=TINTE_2)),
        hoverlabel=dict(bgcolor="white", font_color=TINTE),
    )
    fig.update_xaxes(gridcolor=RASTER, linecolor=ACHSE, zeroline=False)
    fig.update_yaxes(gridcolor=RASTER, linecolor=ACHSE, zeroline=False)
    return fig


def gestapelt(tab: pd.DataFrame, kategorie: str, staende: list, horizontal=True, hoehe=340):
    """tab: Zeilen = Kategorie, Spalten = Stände (Anzahl)."""
    fig = go.Figure()
    for s in staende:
        if s not in tab.columns:
            continue
        marker = dict(color=FARBE[s], line=dict(color="#ffffff", width=2))
        if s == "Frist verpasst":  # Schraffur, damit es nicht mit dem Rot von «Gefährdet» verwechselt wird
            marker["pattern"] = dict(shape="/", fgcolor="#ffffff", size=7, solidity=0.35)
        kw = dict(name=s, marker=marker,
                  hovertemplate=f"%{{{'y' if horizontal else 'x'}}}<br>{s}: %{{{'x' if horizontal else 'y'}}}<extra></extra>")
        if horizontal:
            fig.add_bar(y=tab[kategorie], x=tab[s], orientation="h", **kw)
        else:
            fig.add_bar(x=tab[kategorie].astype(str), y=tab[s], **kw)
    if horizontal:
        fig.update_yaxes(autorange="reversed", type="category")
    else:
        fig.update_xaxes(type="category")
    return _layout(fig, hoehe)


def excel_knopf(label: str, blaetter: dict, info: dict, dateiname: str):
    st.download_button(label, data=excel(blaetter, info), file_name=dateiname, type="primary",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


TABELLEN_CFG = {
    **SPALTEN_CFG,
    "Zuständigkeitsende": st.column_config.DateColumn(format="DD.MM.YYYY"),
    "Erreicht am": st.column_config.DateColumn(format="DD.MM.YYYY"),
    "Tage bis Ende": st.column_config.NumberColumn(format="%d"),
    "Tage ohne Sozialhilfe": st.column_config.NumberColumn(format="%d"),
    "Grund Ziel 1": st.column_config.TextColumn(width="medium"),
    "Grund Ziel 2": st.column_config.TextColumn(width="medium"),
    "Grund Ziel 3": st.column_config.TextColumn(width="medium"),
}


def tabelle(df: pd.DataFrame, key: str, hoehe: int = 420):
    """Tabelle mit Zeilenauswahl. Gibt die gewählte Zeile (Series) oder None zurück."""
    ev = st.dataframe(df, hide_index=True, width="stretch", column_config=TABELLEN_CFG,
                      on_select="rerun", selection_mode="single-row", key=key, height=hoehe)
    rows = ev.selection.rows if ev and ev.selection else []
    return df.iloc[rows[0]] if rows else None


def verteilung(staende: pd.Series, hoehe: int = 96):
    """Eine 100%-Leiste für einen Ziel-Stand."""
    reihen = ["Erreicht", "Erreicht nach Frist", "Auf Kurs", "Gefährdet", "Frist verpasst"]
    sc = staende[staende != "Nicht anwendbar"]
    n = max(1, len(sc))
    fig = go.Figure()
    for s_ in reihen:
        k = int((sc == s_).sum())
        if k == 0:
            continue
        marker = dict(color=FARBE[s_], line=dict(color="#ffffff", width=2))
        if s_ == "Frist verpasst":  # Schraffur zur klaren Unterscheidung von «Gefährdet» (rot)
            marker["pattern"] = dict(shape="/", fgcolor="#ffffff", size=7, solidity=0.35)
        fig.add_bar(y=[""], x=[k / n], orientation="h", name=s_, text=[f"{k}"], textposition="inside",
                    insidetextanchor="middle",
                    textfont=dict(color="#15202b" if s_ in ("Auf Kurs", "Erreicht nach Frist") else "white", family=SCHRIFT),
                    marker=marker,
                    hovertemplate=f"{s_}: {k} ({k / n:.0%})<extra></extra>")
    fig = _layout(fig, hoehe)
    fig.update_xaxes(visible=False, range=[0, 1])
    fig.update_yaxes(visible=False)
    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", margin=dict(l=0, r=0, t=26, b=0))
    return fig


def balken_einfach(x, y, hoehe=300, horizontal=False, farbe=None, prozent=False, referenz=None):
    fig = go.Figure()
    fmt = ".0%" if prozent else "d"
    if horizontal:
        fig.add_bar(y=x, x=y, orientation="h", marker=dict(color=farbe or AARE),
                    hovertemplate="%{y}: %{x:" + fmt + "}<extra></extra>")
        fig.update_yaxes(autorange="reversed", type="category")
        if prozent:
            fig.update_xaxes(tickformat=".0%", range=[0, 1])
        if referenz is not None:
            fig.add_vline(x=referenz, line=dict(color="#15202b", width=1.5, dash="dot"))
    else:
        fig.add_bar(x=x, y=y, marker=dict(color=farbe or AARE), hovertemplate="%{x}: %{y:" + fmt + "}<extra></extra>")
    fig = _layout(fig, hoehe)
    fig.update_layout(showlegend=False)
    return fig


def person_detail_tabellen(d, zemis):
    """Verlauf einer Person: Sprache, Kurse/Ausbildung, Arbeit, Unterstützung des Haushalts."""
    datum = st.column_config.DateColumn(format="DD.MM.YYYY")
    s_ = d["sprache"][d["sprache"]["zemis"] == zemis][["datum", "sprache", "niveau", "art", "bemerkungen"]]
    f = d["foerderung"][d["foerderung"]["zemis"] == zemis][["start", "abschluss", "art", "bezeichnung", "stunden"]]
    e = d["erwerb"][d["erwerb"]["zemis"] == zemis][["von", "bis", "arbeitgeber", "pensum"]]
    dossier = d["klient"][d["klient"]["zemis"] == zemis]["dossier"]
    fu = d["finanz"][d["finanz"]["dossier"].isin(dossier)][["von", "bis", "art", "grund"]]
    a, b = st.columns(2)
    a.caption("Sprachstand")
    a.dataframe(s_.sort_values("datum").rename(columns={"datum": "Datum", "sprache": "Sprache", "niveau": "Niveau",
                "art": "Nachweis", "bemerkungen": "Bemerkungen"}), hide_index=True, width="stretch",
                column_config={"Datum": datum})
    b.caption("Kurse und Ausbildung")
    b.dataframe(f.sort_values("start").rename(columns={"start": "Start", "abschluss": "Abschluss", "art": "Art",
                "bezeichnung": "Bezeichnung", "stunden": "Std./Woche"}), hide_index=True, width="stretch",
                column_config={"Start": datum, "Abschluss": datum})
    a.caption("Arbeit")
    a.dataframe(e.sort_values("von").rename(columns={"von": "Von", "bis": "Bis", "arbeitgeber": "Arbeitgeber",
                "pensum": "Pensum %"}), hide_index=True, width="stretch", column_config={"Von": datum, "Bis": datum})
    b.caption("Unterstützung des Haushalts")
    b.dataframe(fu.sort_values("von").rename(columns={"von": "Von", "bis": "Bis", "art": "Unterstützung",
                "grund": "Grund Beendigung"}), hide_index=True, width="stretch", column_config={"Von": datum, "Bis": datum})
