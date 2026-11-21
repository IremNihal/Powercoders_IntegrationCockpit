# Integrations-Cockpit · Asylsozialdienst Stadt Bern

Prototyp für den AI for Access Hackathon (20.–21.11.2026).
Excel rein, Excel raus: Das Cockpit liest die Exporte aus dem Fallführungssystem und zeigt
für jede:n Klient:in, wie sie oder er beim Integrationsziel steht – und was als Nächstes zu tun ist.

## Starten

```bash
pip install -r requirements.txt
streamlit run app.py
```

Dann im Browser `http://localhost:8501` öffnen.
Demo-Benutzer (Passwort `demo`): `anna`, `david` (Sozialarbeit), `leitung`, `daten`.

Ohne eigene Exporte zeigt die App Demodaten (`daten/demo`, alle Personen erfunden).
Neue Demodaten: `python tools/synthetische_daten.py --personen 400`

## Drei Rollen

| Rolle | Sieht | Frage |
|---|---|---|
| Sozialarbeit | nur eigene Fälle | Wen rufe ich diese Woche an, und warum? |
| Leitung | alle Fälle, Totale, Kohorten, kommende Fristen | Wo stehen wir? Wo müssen wir helfen? |
| Datenverwaltung | Exporte laden, Datenqualität, Gesamtexport | Sind die Daten vollständig? |

## Ordner

```
app.py                  Start, Anmeldung, Navigation nach Rolle
cockpit/
  schema.py             Die 11 Exporte: Dateierkennung und Spaltennamen
  laden.py              Excel lesen, Spalten zuordnen, Schweizer Daten
  regeln.py             Ziel 1, Ampel, Totale, Datenqualität (alle Annahmen oben in REGELN)
  ziele23.py            Ziel 2 (Arbeit/Ausbildung) und Ziel 3 (Haushalt), Ampel-Matrix
  analysen.py           Erfolgsfaktoren (Stufe 2), Fallbelastung, Szenario 2027
  abgeltung.py          Zielerreichung und Abgeltung
  datenbank.py          Lokale SQLite-Datenbank, Schlüsselprüfung, Datenmodell-Diagramm
  export.py             Excel-Ausgabe mit Farben und Filtern
  auth.py               Demo-Anmeldung mit Rollen
  daten.py              Gemeinsamer Datenzugriff mit Cache
ansichten/              Eine Datei pro Rolle + Regeln-Seite
tools/synthetische_daten.py   Erfundene Testdaten in Vorlagen-Format
tests/test_regeln.py    Tests der Regeln
vorlagen/               Export-Vorlagen (6 davon rekonstruiert, siehe Dateiname)
daten/export/           Hier landen die echten Exporte (nicht im Git)
daten/demo/             Demodaten
```

## Stand (Abgleich mit der Challenge)

| Anforderung | Umsetzung |
|---|---|
| Excel rein, Excel raus, nächster Monat mit denselben Klicks | Datenverwaltung: 11 Dateien hochladen, Gesamtexport herunterladen |
| Stufe 1: Ist-Soll Ziel 1, pro Person, pro Fallführung, pro Einreisejahr | ✅ |
| Stufe 2: Was haben erfolgreiche Personen gemeinsam? Nur Gruppen | ✅ Leitung → Erfolgsfaktoren, Gruppen unter 5 ausgeblendet. Situationsanalyse: Konzept lokales Sprachmodell |
| Stufe 3: Ziel 2 (Arbeit/Ausbildung) und Ziel 3 (Haushalt) | ✅ |
| Stufe 4: Ampel pro Person und Ziel, Sicht Sozialarbeit und Leitung | ✅ |
| Prognose Abgeltungen | ✅ Zielerreichung & Abgeltung (Anzahl, optional CHF) |
| Was-wäre-wenn Regeländerung 2027 | ✅ |
| Datenqualität (ZEMIS-Tätigkeit fehlt im Erwerb u.a.) | ✅ |
| Fallbelastung | ✅ |
| Datenschutz / Data Governance | ✅ siehe unten |

Lokale Datenbank: `daten/cockpit.sqlite` (11 Exporte + Ergebnisse, Schlüsselprüfung in «Daten → Datenmodell»).

## Datenschutz (revDSG)

- Läuft auf einem Server im Netz der Stadt. Keine Cloud, kein Internet, keine Telemetrie
  (`gatherUsageStats = false` in `.streamlit/config.toml`). Die Server-Adresse ist fest eingetragen
  (`server.address`), sonst fragt Streamlit beim Start einen Dienst im Internet nach der öffentlichen IP.
  Die Schrift liegt lokal im Ordner `static`.
- Anmeldung im Betrieb über das bestehende Login der Stadt (SSO/AD), Rolle aus der AD-Gruppe.
- Sozialarbeit sieht nur eigene Fälle. Exporte enthalten nur, was die Rolle braucht.
- KI (z.B. für die Situationsanalyse) nur mit einem lokalen Modell auf demselben Server.
  Aus dem Freitext werden nur wenige Felder gelesen (Alphabetisierung, Schuljahre, Berufserfahrung);
  Gesundheitsangaben werden nicht verarbeitet.
- Auswertungen zu Erfolgsfaktoren nur auf Gruppen, nie ein Score pro Person.

## Offene Fragen an das ASD

- Welche «Art» im Sprachstand zählt als A1-Nachweis? Steht der Nachweis (fide, telc …) immer in den Bemerkungen?
- Nutzt ihr intern die Vorgabe A1 nach 12 / 24 Monaten?
- Gilt für Personen, die nach der Einreise 16 werden, die Frist ab dem 16. Geburtstag?
- Kinder, die in der Schweiz geboren sind: Welches Datum gilt?
- Ziel 2: Zählen zwei Stellen zusammen (z.B. 30 % + 30 %)? Gilt eine neue Stelle ab dem Folgetag als «ohne Unterbruch»?
- Ziel 3: Ist eine Lücke ohne Eintrag auch «keine Unterstützung»? Zählt Nothilfe wie Sozialhilfe?
- Regeländerung 2027: Gilt «5 Jahre ab Einreise» auch für Personen, die heute schon länger als 5 Jahre da sind (Ende am 01.01.2027)?
