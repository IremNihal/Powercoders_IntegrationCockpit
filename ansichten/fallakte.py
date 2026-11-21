"""Fallakte (Object Page): eine Person auf einen Blick – Kopf, drei Ziele, Zeitstrahl, Verlauf."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from cockpit.regeln import AMPEL
from ansichten import ui

ZIEL = {1: "Sprache A1", 2: "Arbeit / Ausbildung", 3: "Haushalt ohne Sozialhilfe"}
SPUREN = ["Sprache", "Kurse & Ausbildung", "Arbeit", "Sozialhilfe (Haushalt)"]


def zeitstrahl(d, zemis, z1row, z3row, stichtag):
    st_ = pd.Timestamp(stichtag)
    fig = go.Figure()

    def balken(spur, von, bis, farbe, text):
        bis = bis if pd.notna(bis) else st_
        fig.add_trace(go.Scatter(x=[von, bis], y=[spur, spur], mode="lines", line=dict(color=farbe, width=14),
                                 hovertemplate=f"{text}<br>{von:%d.%m.%Y} – {bis:%d.%m.%Y}<extra></extra>", showlegend=False))

    f = d["foerderung"][d["foerderung"]["zemis"] == zemis]
    for _, r in f.iterrows():
        if pd.notna(r["start"]):
            farbe = ui.AARE if str(r["art"]) in ("Sek II", "Tertiär") else "#7fb5b8"
            balken("Kurse & Ausbildung", r["start"], r["abschluss"], farbe, f"{r['art']}: {r['bezeichnung']}")
    e = d["erwerb"][d["erwerb"]["zemis"] == zemis]
    for _, r in e.iterrows():
        if pd.notna(r["von"]):
            p = pd.to_numeric(r["pensum"], errors="coerce")
            balken("Arbeit", r["von"], r["bis"], "#0ca30c" if p >= 60 else "#8fcf8f", f"{r['arbeitgeber']} ({p:.0f} %)")
    fu = d["finanz"][d["finanz"]["dossier"] == z1row["dossier"]]
    for _, r in fu.iterrows():
        if pd.notna(r["von"]):
            sh = str(r["art"]).lower() in ("sozialhilfe", "nothilfe")
            balken("Sozialhilfe (Haushalt)", r["von"], r["bis"], "#9aa6b2" if sh else "#e2f0f0", str(r["art"]))
    s = d["sprache"][d["sprache"]["zemis"] == zemis]
    if not s.empty:
        fig.add_trace(go.Scatter(
            x=s["datum"], y=["Sprache"] * len(s), mode="markers+text", text=s["niveau"], textposition="bottom center",
            textfont=dict(size=11, color=ui.TINTE),
            marker=dict(size=13, color=["#ffffff" if str(a) == "Einschätzung" else ui.AARE for a in s["art"]],
                        line=dict(color=ui.AARE, width=2)),
            hovertemplate=[f"{n} ({a})<br>%{{x|%d.%m.%Y}}<extra></extra>" for n, a in zip(s["niveau"], s["art"])],
            showlegend=False))

    marken = [("Einreise", z1row.get("einreise"), "#15202b"), ("Frist A1", z1row.get("frist"), ui.FARBE["Gefährdet"]),
              ("Zuständigkeitsende", z3row.get("zust_ende") if z3row is not None else None, "#5b6672"),
              ("Heute", st_, ui.AARE)]
    for name, datum, farbe in marken:
        if datum is not None and pd.notna(datum):
            fig.add_vline(x=datum, line=dict(color=farbe, width=1.5, dash="dot" if name != "Heute" else "solid"))
            fig.add_annotation(x=datum, y=1.09, yref="paper", text=name, showarrow=False,
                               font=dict(size=11, color=farbe), xanchor="left" if name != "Heute" else "right")
    fig = ui._layout(fig, 270)
    fig.update_yaxes(categoryorder="array", categoryarray=SPUREN[::-1], type="category", showgrid=False)
    fig.update_xaxes(tickformat="%Y", dtick="M12", showgrid=True)
    fig.update_layout(margin=dict(l=8, r=8, t=40, b=8), showlegend=False)
    return fig


@st.dialog("Fallakte", width="large")
def oeffnen(ctx, zemis):
    d, stichtag = ctx["d"], ctx["stichtag"]
    m = ctx["matrix"].set_index("zemis").loc[zemis]
    z1 = ctx["z1"].set_index("zemis").loc[zemis]
    z3 = ctx["z3"].set_index("dossier")
    z3row = z3.loc[m["dossier"]] if m["dossier"] in z3.index else None
    einreise = f"{z1['einreise']:%d.%m.%Y}" if pd.notna(z1["einreise"]) else "–"
    st.markdown(
        f'<div class="akte-kopf"><div><div class="akte-titel">Klient:in {m["klientennr"]}</div>'
        f'<div class="akte-chips"><span>{m["status"]}</span><span>{int(m["alter"])} Jahre</span>'
        f'<span>Haushalt {m["dossier"]}</span><span>Einreise {einreise}</span><span>{m["sozialarbeit"]}</span></div></div></div>',
        unsafe_allow_html=True)
    karten = []
    for i in (1, 2, 3):
        stand = m[f"stand{i}"]
        schritt = m[f"schritt{i}"] if isinstance(m[f"schritt{i}"], str) else ""
        karten.append(
            f'<div class="ziel-karte" style="border-top-color:{ui.FARBE.get(stand, "#d6d5ce")}">'
            f'<div class="ziel-name">Ziel {i}: {ZIEL[i]}</div><div class="ziel-stand">{AMPEL[stand]} {stand}</div>'
            f'<div class="ziel-grund">{m[f"grund{i}"]}</div>'
            + (f'<div class="ziel-schritt">{schritt}</div>' if schritt else "") + '</div>')
    st.markdown(f'<div class="ziel-reihe">{"".join(karten)}</div>', unsafe_allow_html=True)
    ui.abschnitt("Zeitstrahl", "Sprache, Kurse, Arbeit und Unterstützung seit der Einreise")
    st.plotly_chart(zeitstrahl(d, zemis, z1, z3row, stichtag), width="stretch", config={"displayModeBar": False})
    with st.expander("Alle Einträge als Tabelle"):
        ui.person_detail_tabellen(d, zemis)
