"""Transparenz: Welche Regeln rechnet das Cockpit? (für alle Rollen)"""
import streamlit as st
from cockpit.regeln import REGELN
from ansichten import ui


def zeigen(ctx):
    ui.kopf("So rechnet das Cockpit", "Alle Regeln an einem Ort. Annahmen sind markiert und können angepasst werden.")
    st.markdown(f"""
**Wer zählt für Ziel 1 (Sprache A1)?**
- Aktuelle Klient:innen: Zuständigkeitsende noch nicht erreicht, nicht an die Gemeinde übergeben.
- Status (am Stichtag, aus der Status-Historie): {", ".join(sorted(REGELN["status_ziel1"]))}. Status S und N zählen nicht.
- Ab {REGELN["mindestalter"]} Jahren.

**Frist**
- Einreise = Ereignis «Aufenthalt (Einreise)» in den Asylgeschäftsdaten.
- Frist = Einreise + {REGELN["frist_jahre_ziel1"]} Jahre.
- ⚠️ *Annahme:* Wer erst nach der Einreise 16 wird, hat 3 Jahre ab dem 16. Geburtstag.

**Was gilt als A1-Nachweis?**
- Sprachstand A1 oder höher in Deutsch oder Französisch, mit Datum, und
  - Art «Zertifikat» **mit** telc oder fide in den Bemerkungen, oder
  - Art «Muttersprache», «Schulbesuch in der Schweiz» oder «Abgeschlossene Ausbildung».
- Oder: Ziel ist in der Integrationszielerreichung erfasst.
- Eine «Einschätzung» zählt nicht – sie wird aber als *schneller Erfolg* gezeigt (A1 da, Prüfung fehlt).

**Ziel 2: Arbeit oder Ausbildung** (VA und FL ab 16, vor Zuständigkeitsende)
- Arbeit mit Pensum ≥ 60 % während 6 Monaten ohne Unterbruch (Tabelle Erwerb).
  ⚠️ *Annahme:* Eine neue Stelle ab dem Folgetag gilt als ohne Unterbruch; mehrere Stellen werden nicht addiert.
- Oder Ausbildung «Sek II» oder «Tertiär» (Tabelle Integrationsförderung und Ausbildung).
- 🟡 wenn eine Stelle ≥ 60 % läuft, ein Brückenangebot läuft oder genug Zeit bleibt. 🔴 wenn weniger als 12 Monate bleiben
  und weder Arbeit noch Ausbildung da ist, oder weniger als 6 Monate (dann nur noch über Ausbildung möglich).

**Ziel 3: 12 Monate ohne Sozialhilfe** (pro Haushalt, Dossier-Nr., vor Zuständigkeitsende)
- Aus der Tabelle Finanzielle Unterstützung: eine Lücke von 12 Monaten ohne «Sozialhilfe».
  ⚠️ *Annahme:* «Nothilfe» zählt wie Sozialhilfe. Zuständigkeitsende des Haushalts = spätestes Ende der Mitglieder.
- 🔴 wenn der Haushalt noch unterstützt wird und weniger als 18 Monate bleiben. ⚫ wenn weniger als 12 Monate bleiben.

**Ampel**
- 🟢 Erreicht (in Frist), 🟡 Auf Kurs, 🔴 Gefährdet, ⚫ Frist verpasst, ⚪ Nicht anwendbar
- 🔴 Gefährdet: Frist in weniger als {REGELN["rot_tage"]} Tagen, oder in weniger als {REGELN["gelb_risiko_tage"]} Tagen und kein Deutschkurs.


**Datenschutz**
- Läuft auf einem Server im Netz der Stadt. Keine Daten gehen ins Internet, keine Cloud, keine externe KI.
- Jede Rolle sieht nur, was sie braucht. Sozialarbeit sieht nur eigene Fälle.
- Auswertungen zu Erfolgsfaktoren nur auf Gruppen, nie ein Score pro Person.
""")
