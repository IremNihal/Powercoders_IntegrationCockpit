"""Integrations-Cockpit · Asylsozialdienst Stadt Bern (Prototyp, AI for Access Hackathon 2026)

Start:  streamlit run app.py

Die Oberfläche ist das Mockup (cockpit-mockup.html). Die Daten kommen aus den echten
Exporten: über die bestehenden Regeln (regeln/ziele23) berechnet, von build_daten.py in das
Mockup-Format gebracht und als window.R_DATA in die Seite eingefügt. Keine erfundenen Daten,
keine echten Namen – nur synthetische Demodaten bzw. hochgeladene Exporte.
"""
from datetime import date
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from cockpit.auth import pruefen, ROLLEN_TEXT  # noqa: F401  (Login bleibt erhalten, im Demo-Modus übersprungen)
from cockpit import daten
from cockpit.export import excel
from cockpit.regeln import fuer_anzeige, totale
from cockpit.ziele23 import anzeige_matrix, anzeige_z2, anzeige_z3
import build_daten

st.set_page_config(page_title="Integrations-Cockpit", page_icon=":material/explore:", layout="wide")

ROOT = Path(__file__).parent
MOCKUP = ROOT / "cockpit-mockup.html"
MOCKUP4 = ROOT / "mockup4.html"


def login():
    """Demo-Login. Im Demo-Modus übersprungen – bleibt für den Betrieb (SSO/AD) erhalten."""
    links, rechts = st.columns([1.15, 1], gap="large")
    with rechts:
        with st.form("login", border=False):
            b = st.text_input("Benutzer")
            p = st.text_input("Passwort", type="password")
            if st.form_submit_button("Anmelden", type="primary", width="stretch"):
                u = pruefen(b, p)
                if u:
                    st.session_state["user"] = u
                    st.rerun()
                st.error("Benutzer oder Passwort falsch.")


def export_bytes(stichtag, r) -> bytes:
    blaetter = {
        "Ampel pro Person": anzeige_matrix(r["matrix"]),
        "Ziel 1 Sprache": fuer_anzeige(r["z1"]),
        "Ziel 2 Arbeit": anzeige_z2(r["z2"]),
        "Ziel 3 Haushalt": anzeige_z3(r["z3"]),
        "Ziel 1 pro Fallführung": totale(r["z1"], "sozialarbeit"),
    }
    info = {"Stichtag": f"{stichtag:%d.%m.%Y}",
            "Datenquelle": "Demodaten (synthetisch)" if daten.ist_demo() else "Exporte ASD",
            "Hinweis": "Synthetische Demodaten, keine echten Personen" if daten.ist_demo() else ""}
    return excel(blaetter, info)


# ---------- Sidebar: Steuerungen ----------
with st.sidebar:
    st.markdown("### Integrations-Cockpit")
    st.caption("Asylsozialdienst Stadt Bern")
    quelle_demo = daten.ist_demo()
    quelle_wahl = st.radio("Datenquelle", ["Synthetische Demodaten", "Eigene Exporte hochladen"],
                           index=0 if quelle_demo else 1)
    if quelle_wahl == "Eigene Exporte hochladen" and quelle_demo:
        st.caption("Exporte (.xlsx) nach `daten/export` legen – sie werden dann automatisch verwendet.")
    elif not quelle_demo:
        st.caption("Eigene Exporte in `daten/export` werden verwendet.")
    stichtag = st.date_input("Stichtag", value=date(2026, 11, 21), format="DD.MM.YYYY")

# Login bleibt im Code, wird im Demo-Betrieb übersprungen.
_ = st.session_state.get("user")

# ---------- Daten berechnen (bestehende Regeln) ----------
d, berichte, r = daten.alles(stichtag)
st.session_state["_stichtag"] = stichtag
st.session_state["_demo"] = daten.ist_demo()

with st.sidebar:
    st.download_button("⬇️ Excel exportieren", data=export_bytes(stichtag, r),
                       file_name=f"Integrations-Cockpit_{stichtag:%Y%m%d}.xlsx", width="stretch",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("Verarbeitung nur lokal. Demodaten sind erfunden, keine echten Namen.")

# ---------- Mockup mit echten Daten füllen ----------
import json

r_json = json.dumps(build_daten.baue(d, stichtag), ensure_ascii=False)
inject = f"<script>window.R_DATA = {r_json};</script>\n</head>"
html_cockpit = MOCKUP.read_text(encoding="utf-8").replace("</head>", inject, 1)
html_mockup = MOCKUP4.read_text(encoding="utf-8").replace("</head>", inject, 1)

tab_cockpit, tab_mockup = st.tabs(["Cockpit", "Mockup"])
with tab_cockpit:
    components.html(html_cockpit, height=1500, scrolling=True)
with tab_mockup:
    # Klickbarer Mockup mit denselben Excel-Daten wie Cockpit (window.R_DATA).
    # Höhe so gewählt, dass der iframe ins Fenster passt – sonst öffnen die <dialog>-Fenster
    # ausserhalb des sichtbaren Bereichs. Ein einzelner Scrollbalken (im iframe) genügt.
    components.html(html_mockup, height=820, scrolling=True)
