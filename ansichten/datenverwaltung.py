"""Ansicht Datenverwaltung: Exporte hochladen, prüfen, Datenqualität, Gesamtexport."""
import streamlit as st

from cockpit.daten import EXPORT, DB, ist_demo
from cockpit import datenbank
from ansichten.leitung import ist_soll
from cockpit.ziele23 import anzeige_matrix, anzeige_z2, anzeige_z3
from cockpit.schema import TABELLEN, tabelle_aus_dateiname
from cockpit.regeln import totale, fuer_anzeige
from ansichten import ui


def zeigen(ctx):
    berichte, z1, dq, stichtag = ctx["berichte"], ctx["z1"], ctx["dq"], ctx["stichtag"]
    db = ctx["db"]
    ui.kopf("Daten", "Monatliche Exporte laden, prüfen und als Excel zurückgeben")

    t1, t4, t2, t3 = st.tabs(["Exporte laden", "Datenmodell", "Datenqualität", "Export"])
    with t1:
        ui.abschnitt("1. Die 11 Exporte hierher ziehen", "Die Tabelle wird am Dateinamen erkannt, z.B. «Hackathon_Klient_Resultat.xlsx». Die Dateien bleiben auf diesem Server.")
        dateien = st.file_uploader("Excel-Dateien", type=["xlsx"], accept_multiple_files=True,
                                   label_visibility="collapsed")
        if dateien:
            erkannt = [(f, tabelle_aus_dateiname(f.name)) for f in dateien]
            for f, key in erkannt:
                st.write(("✅ " + TABELLEN[key]["titel"]) if key else "❓ nicht erkannt", "–", f.name)
            if st.button("Übernehmen", type="primary"):
                EXPORT.mkdir(parents=True, exist_ok=True)
                for f, key in erkannt:
                    if not key:
                        continue
                    for alt in EXPORT.glob("*.xlsx"):
                        if tabelle_aus_dateiname(alt.name) == key:
                            alt.unlink()
                    (EXPORT / f.name).write_bytes(f.getbuffer())
                st.cache_data.clear()
                st.rerun()
        if not ist_demo():
            if st.button("Alle Exporte entfernen und Demodaten zeigen"):
                for f in EXPORT.glob("*.xlsx"):
                    f.unlink()
                st.cache_data.clear()
                st.rerun()

        ui.abschnitt("2. Was wurde erkannt?", "Grün: alle Pflichtspalten da. Rot: Pflichtspalten fehlen. Grau: Datei fehlt.")
        gefunden = {b.tabelle: b for b in berichte}
        zeilen = []
        for key, spec in TABELLEN.items():
            b = gefunden.get(key)
            if not b:
                zeilen.append({"": "⚪", "Tabelle": spec["titel"], "Datei": "fehlt", "Zeilen": 0,
                               "Pflichtspalten fehlen": "", "Nicht verwendete Spalten": ""})
            else:
                zeilen.append({"": "🔴" if b.fehlend_pflicht else "🟢", "Tabelle": spec["titel"], "Datei": b.datei,
                               "Zeilen": b.zeilen, "Pflichtspalten fehlen": ", ".join(b.fehlend_pflicht),
                               "Nicht verwendete Spalten": ", ".join(map(str, b.unbekannt))})
        st.dataframe(zeilen, hide_index=True, width="stretch", height=38 * 12)

    with t4:
        ui.abschnitt("So hängen die Tabellen zusammen", "Klient ist die Drehscheibe. Personen über Zemis-Nr. oder Klientennummer, Haushalte über die Dossier-Nr.")
        st.graphviz_chart(datenbank.er_diagramm(), width="stretch")
        ui.abschnitt("Schlüsselprüfung", "Zeilen, deren Schlüssel in der Zieltabelle fehlt, gehen bei der Auswertung verloren.")
        b = db["beziehungen"].copy()
        b.insert(0, "", b["Ohne Treffer"].map(lambda n: "🟢" if n == 0 else "🔴"))
        st.dataframe(b, hide_index=True, width="stretch")
        if db["klient_doppelt"]:
            st.warning(f"{db['klient_doppelt']} Klientennummern kommen in der Tabelle Klient mehrfach vor. Es wird die erste Zeile verwendet.")
        ui.abschnitt("Lokale Datenbank", "Alle Exporte und Ergebnisse in einer Datei (SQLite) auf diesem Server. "
                     "Kann im Netz der Stadt z.B. mit Excel oder Power BI gelesen werden.")
        st.code(str(DB), language=None)
        st.caption("Tabellen: die 11 Exporte plus ergebnis_ziel1, ergebnis_ziel2, ergebnis_ziel3, ergebnis_ampel. "
                   "Die Datei wird bei jedem neuen Export neu geschrieben.")

    with t2:
        if dq.empty:
            st.success("Keine Auffälligkeiten gefunden.")
        else:
            zaehl = dq["Kategorie"].value_counts()
            ui.kacheln([(k, int(v), "", None) for k, v in zaehl.items()])
            kat = st.multiselect("Kategorie", list(zaehl.index), default=list(zaehl.index))
            st.dataframe(dq[dq["Kategorie"].isin(kat)], hide_index=True, width="stretch", height=420)
            st.caption("«Geld nicht abgeholt»: Ziel ist erreicht, aber nicht in der Integrationszielerreichung erfasst. "
                       "«Nicht gemeldete Arbeit?»: Job in ZEMIS, aber nicht im Erwerb.")

    with t3:
        ui.abschnitt("Gesamtexport", "Jeden Monat gleich: Exporte laden, dann hier herunterladen.")
        ui.excel_knopf("Gesamtexport herunterladen", {
            "Ampel pro Person": anzeige_matrix(ctx["matrix"]),
            "Ziel 1 Sprache": fuer_anzeige(z1),
            "Ziel 2 Arbeit": anzeige_z2(ctx["z2"]),
            "Ziel 3 Haushalt": anzeige_z3(ctx["z3"]),
            "Stufe 1 Ist-Soll pro SA": ist_soll(z1, stichtag, "sozialarbeit", "Fallführung"),
            "Stufe 1 Ist-Soll pro Jahr": ist_soll(z1, stichtag, "einreisejahr", "Einreisejahr"),
            "Ziel 1 pro Fallführung": totale(z1, "sozialarbeit"),
            "Ziel 2 pro Fallführung": totale(ctx["z2"], "sozialarbeit"),
            "Ziel 3 pro Fallführung": totale(ctx["z3"], "sozialarbeit"),
            "Ziel 1 pro Einreisejahr": totale(z1[z1["im_scope"]], "einreisejahr"),
            "Datenqualität": dq,
        }, {"Bericht": "Integrations-Cockpit, Ziele 1 bis 3", "Stichtag": f"{stichtag:%d.%m.%Y}",
            "Datenquelle": ctx["quelle"]}, f"Ziel1_Gesamt_{stichtag:%Y%m%d}.xlsx")
