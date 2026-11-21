"""Erzeugt synthetische Exporte (11 Tabellen) im Format der ASD-Vorlagen.

Alle Personen sind erfunden. Die Daten haben eingebaute Muster
(Alphabetisierung, Schuljahre, Alter, Deutschkurse -> A1), damit Level 2 etwas finden kann,
und ein paar absichtliche Datenfehler für die Datenqualitäts-Prüfung.

Aufruf:  python tools/synthetische_daten.py  [--personen 400] [--ziel daten/demo]
"""
import argparse
import random
from datetime import date, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Font

STICHTAG = date(2026, 11, 20)
SOZIALARBEIT = ["Anna Muster", "Marco Beispiel", "Lea Probst", "Samir Haddad",
                "Nina Keller", "Jonas Frei", "Sara Bianchi", "David Roth"]
LAENDER = [  # (Land, Muttersprache, Anteil, Alphabetisiert-Wahrscheinlichkeit, Ø Schuljahre)
    ("Afghanistan", "Dari", 0.22, 0.45, 5),
    ("Eritrea", "Tigrinya", 0.20, 0.55, 6),
    ("Syrien", "Arabisch", 0.15, 0.80, 9),
    ("Türkei", "Türkisch", 0.12, 0.95, 10),
    ("Somalia", "Somali", 0.07, 0.35, 4),
    ("Irak", "Kurdisch", 0.08, 0.70, 8),
    ("Iran", "Farsi", 0.06, 0.90, 11),
    ("Ukraine", "Ukrainisch", 0.10, 0.99, 12),
]
AUSBILDUNG = ["Keine", "Primarschule", "Sekundarstufe I", "Sekundarstufe II", "Tertiär"]
ARBEITGEBER = [("Alters- und Pflegeheim Wattenwil", "Wattenwil"), ("Altersbetreuung Worb", "Worb"),
               ("Hotel Bellevue Bern", "Bern"), ("Coop Gastronomie", "Bern"), ("Reinigung Blitz AG", "Ostermundigen"),
               ("Logistik Mitte AG", "Zollikofen"), ("Bäckerei Glatz", "Bern"), ("Spital Tiefenau", "Bern"),
               ("Gartenbau Grün GmbH", "Köniz"), ("Migros Verteilbetrieb", "Schönbühl")]
TEMP = ["Adecco", "Adecco Hotel & Event Bern Personalberatung", "4 You Personal AG / Einsatzort Kanton Basel-Stadt"]

R = random.Random(42)


def d(x: date) -> date:
    return x


def plus_jahre(x: date, j: int) -> date:
    try:
        return x.replace(year=x.year + j)
    except ValueError:
        return x.replace(year=x.year + j, day=28)


def zufallsdatum(von: date, bis: date) -> date:
    return von + timedelta(days=R.randint(0, max(0, (bis - von).days)))


def schreiben(pfad: Path, kopf: list, zeilen: list, datum_als_text=False):
    wb = Workbook()
    ws = wb.active
    ws.title = "Tabelle1"
    ws.append(kopf)
    for c in ws[1]:
        c.font = Font(bold=True)
    for z in zeilen:
        werte = []
        for v in z:
            if isinstance(v, date) and datum_als_text:
                werte.append(v.strftime("%d.%m.%Y"))
            else:
                werte.append(v)
        ws.append(werte)
    for col in ws.iter_cols(min_row=2):
        for c in col:
            if isinstance(c.value, date):
                c.number_format = "DD.MM.YYYY"
    for i, k in enumerate(kopf, start=1):
        ws.column_dimensions[ws.cell(1, i).column_letter].width = max(12, len(k) + 2)
    wb.save(pfad)


def situationsanalyse_text(dossier: str, zemis: str, land: str, mutter: str, groesse: int,
                           alpha: bool, sj: int, aj: int) -> str:
    """Kurzer Freitext-Bericht pro Haushalt mit eingebetteten, auslesbaren Hinweisen.

    Enthält bewusst KEINEN Abschnitt Gesundheit – Gesundheitsangaben sollen gar nicht
    erst in die Berichte gelangen. Die auslesbaren Angaben (Alphabetisierung, Schuljahre,
    Berufserfahrung) stehen in natürlicher Sprache, damit die regelbasierte Extraktion
    etwas zu finden hat.
    """
    alpha_satz = (R.choice([
        "In lateinischer Schrift alphabetisiert.",
        "Die Person ist alphabetisiert und kommt mit Schrift gut zurecht.",
        "Lesen und Schreiben in lateinischer Schrift sind vorhanden (alphabetisiert).",
    ]) if alpha else R.choice([
        "Nicht alphabetisiert; der Alphabetisierungskurs läuft.",
        "Analphabetismus in lateinischer Schrift, Grundkurs begonnen.",
        "Die Person ist nicht alphabetisiert und braucht einen Alpha-Kurs.",
    ]))
    wohnen = R.choice([
        "Wohnt zunächst in einer Kollektivunterkunft, Wechsel in eine eigene Wohnung ist geplant.",
        "Lebt in einer Wohngemeinschaft in Bern, die Lage ist stabil.",
        "In einer eigenen Wohnung untergebracht; das Umfeld ist unterstützend.",
    ])
    potenzial = R.choice([
        "Wirkt motiviert und zuverlässig, erscheint regelmässig zu Terminen.",
        "Zeigt Eigeninitiative bei der Stellensuche und beim Deutschlernen.",
        "Braucht Begleitung bei Behördengängen, bleibt aber dran.",
    ])
    return (
        f"Situationsanalyse Familie – Dossier {dossier}\n"
        f"Zemis-Nr.: {zemis}\n\n"
        f"Familie\n"
        f"Haushalt mit {groesse} Person(en). Herkunft {land}, Muttersprache {mutter}.\n\n"
        f"Wohnen\n{wohnen}\n\n"
        f"Sprache\n{alpha_satz} Vor der Einreise wurden {sj} Schuljahre besucht.\n\n"
        f"Arbeit\n{aj} Jahre Berufserfahrung vor der Einreise. "
        f"{R.choice(['Sucht aktuell eine Anstellung.', 'Teilzeit tätig.', 'Noch keine Anstellung in der Schweiz.'])}\n\n"
        f"Potenzial\n{potenzial}\n"
    )


def erzeugen(n_personen: int, ziel: Path):
    ziel.mkdir(parents=True, exist_ok=True)
    sa_dir = ziel / "situationsanalysen"
    sa_dir.mkdir(parents=True, exist_ok=True)
    klient, asyl, verfahren, sprache, foerd, erwerb, zemis_t = [], [], [], [], [], [], []
    finanz, dossierp, unterbr, zielerr = [], [], [], []

    zemis_nr, kl_nr, dossier_nr = 10_000_000, 20_000, 30_000
    personen = 0
    while personen < n_personen:
        dossier_nr += 1
        dossier = f"D12.{dossier_nr}"
        land, mutter, _, p_alpha, schule = R.choices(LAENDER, weights=[l[2] for l in LAENDER])[0]
        einreise = zufallsdatum(date(2019, 1, 1), date(2026, 8, 31))
        asylgesuch = einreise + timedelta(days=R.randint(1, 20))
        # Status des Haushalts
        if land == "Ukraine":
            status = R.choices(["S", "B-FL"], weights=[0.85, 0.15])[0]
        else:
            status = R.choices(["B-FL", "VA", "F-FL", "B-RSFL", "B-SL", "N"],
                               weights=[0.40, 0.33, 0.15, 0.04, 0.03, 0.05])[0]
        entscheid = asylgesuch + timedelta(days=R.randint(60, 420))
        if status in ("B-FL", "B-RSFL", "B-SL"):
            zust_ende = plus_jahre(asylgesuch, 5)
        elif status in ("VA", "F-FL"):
            zust_ende = plus_jahre(einreise, 7)
        else:
            zust_ende = plus_jahre(einreise, 5)
        sa = R.choice(SOZIALARBEIT)
        groesse = R.choices([1, 2, 3, 4, 5, 6], weights=[0.38, 0.14, 0.14, 0.16, 0.11, 0.07])[0]
        mitglieder = []
        erwachsener_alter = R.randint(19, 55)
        for i in range(groesse):
            if i == 0:
                rolle, bez, alter = "Dossiermitglied", "Dossierträger/-in", erwachsener_alter
            elif i == 1 and groesse > 1 and R.random() < 0.75:
                rolle, bez, alter = "Dossiermitglied", "Ehefrau / -mann", max(18, erwachsener_alter + R.randint(-6, 6))
            else:
                rolle, bez = "Dossiermitglied", "Tochter / Sohn"
                alter = R.randint(0, max(1, min(22, erwachsener_alter - 18)))
            geb = einreise - timedelta(days=int(alter * 365.25) + R.randint(0, 364))
            mitglieder.append((rolle, bez, geb))

        haushalt_erwerb = False
        kopf = None
        for m_i, (rolle, bez, geb) in enumerate(mitglieder):
            zemis_nr += R.randint(1, 50)
            kl_nr += 1
            personen += 1
            z, k = str(zemis_nr), str(kl_nr)
            alter_einreise = (einreise - geb).days / 365.25
            geschlecht = R.choice(["weiblich", "männlich"])
            erwachsen = alter_einreise >= 16
            alpha = R.random() < (p_alpha if erwachsen else 0.9)
            sj = max(0, int(R.gauss(schule, 3))) if erwachsen else max(0, int(alter_einreise) - 6)
            aj = max(0, int(R.gauss(6, 5))) if alter_einreise > 20 else 0
            ausb = (AUSBILDUNG[min(4, sj // 4)] if erwachsen else "Keine")
            if m_i == 0:  # Dossierträger:in – Grundlage für den Situationsanalyse-Bericht des Haushalts
                kopf = {"zemis": z, "alpha": alpha, "sj": sj, "aj": aj}
            if alpha:
                analph = "(Leer)"
            else:
                analph = R.choice(["primär", "sekundär", "funktional"])
            uebergang = zust_ende if zust_ende < STICHTAG else None
            # 2 Personen absichtlich ohne Sozialarbeiter:in (Datenqualität)
            sa_feld = sa if R.random() > 0.005 else None
            klient.append([k, z, dossier, einreise, zust_ende, uebergang, status,
                           "Sozialhilfe", sa_feld, geb, geschlecht, land, R.choice(["ledig", "verheiratet"]) if erwachsen else "ledig",
                           mutter, ausb, sj, alpha, analph, aj])
            dossierp.append([dossier, k, z, einreise, None, rolle, bez])

            # Asylgeschäftsdaten (Einreise fehlt absichtlich bei ~1 %)
            if R.random() > 0.01:
                asyl.append([z, k, "Aufenthalt (Einreise)", einreise, "Einreise erfolgt", 1001, einreise])
            asyl.append([z, k, "Asylgesuch in CH (Kt normal, Kat. III)", asylgesuch,
                         {"B-FL": "Asylgewährung Art. 3, 7", "B-RSFL": "Asylgewährung Art. 51.1",
                          "B-SL": "Anerkennung Staatenlosigkeit", "VA": "Ablehnung",
                          "F-FL": "Ablehnung mit Fl.-Eigenschaft Art 3, 7"}.get(status, "Gegenstandslos"),
                         R.randint(1000, 9999), entscheid if status != "N" else None])
            if R.random() < 0.3:
                asyl.append([z, k, "Identitätsabklärung Asyl", einreise + timedelta(days=30), "Dokument echt", 2001,
                             einreise + timedelta(days=60)])

            # Verfahrensstand: N -> Endstatus
            if status == "S":
                verfahren.append([z, k, dossier, "S", einreise, None])
            else:
                verfahren.append([z, k, dossier, "N", asylgesuch, entscheid - timedelta(days=1) if status != "N" else None])
                if status != "N":
                    verfahren.append([z, k, dossier, status, entscheid, None])

            # Unterbringung
            umzug = einreise + timedelta(days=R.randint(120, 700))
            unterbr.append([k, einreise, umzug if umzug < STICHTAG else None, "Kollektivunterkunft", "3014 Bern"])
            if umzug < STICHTAG:
                unterbr.append([k, umzug, None, R.choice(["Eigene Wohnung", "Wohngemeinschaft"]),
                                R.choice(["3008 Bern", "3013 Bern", "3018 Bern", "3027 Bern"])])

            if not erwachsen and alter_einreise < 12:
                # Kinder: Schule in der Schweiz -> A1 über Schulbesuch, wenn alt genug
                if (STICHTAG - geb).days / 365.25 >= 16:
                    dat = plus_jahre(geb, 16)
                    sprache.append([z, k, "Deutsch", "B1", "Schulbesuch in der Schweiz", dat, "Volksschule Bern"])
                continue

            # ---------- Spracherwerb (eingebaute Muster) ----------
            jahre_hier = (STICHTAG - einreise).days / 365.25
            chance = 0.25 + 0.35 * alpha + 0.03 * min(sj, 12) - 0.006 * max(0, alter_einreise - 30)
            kurs = R.random() < (0.55 + 0.25 * alpha)
            if kurs:
                chance += 0.20
            chance = min(0.95, max(0.03, chance))
            # Deutschkurs(e)
            if kurs:
                ks = einreise + timedelta(days=R.randint(30, 300))
                if ks < STICHTAG:
                    dauer = R.randint(90, 360)
                    ke = ks + timedelta(days=dauer)
                    foerd.append([z, k, ks, ke if ke < STICHTAG else None,
                                  "Alphabetisierungskurs" if not alpha else "Deutschkurs",
                                  "Alpha Deutsch" if not alpha else R.choice(["Deutsch A1 Intensiv", "Deutsch A1/A2 Abend"]),
                                  R.choice([6, 8, 12, 16]), R.choice(["Sprachschule Bern", "Kompetenzzentrum Integration", "isa Bern"]), None])
            if mutter == "Deutsch":
                pass
            erreicht_tage = int(R.gauss(520, 200) / max(chance, 0.2))
            a1_datum = einreise + timedelta(days=max(150, erreicht_tage))
            if R.random() < chance and a1_datum < STICHTAG:
                nachweis = R.choices(["Zertifikat", "Abgeschlossene Ausbildung"], weights=[0.93, 0.07])[0]
                bem = R.choice(["telc A1", "fide A1/A1", "telc Deutsch A1", "fide"]) if nachweis == "Zertifikat" else "Lehrabschluss EBA"
                # absichtlicher Fehler: Zertifikat ohne telc/fide-Angabe
                if nachweis == "Zertifikat" and R.random() < 0.03:
                    bem = None
                sprache.append([z, k, "Deutsch", "A0", "Einschätzung", einreise + timedelta(days=40), "Erstgespräch"])
                sprache.append([z, k, "Deutsch", "A1", nachweis, a1_datum, bem])
                if R.random() < 0.35:
                    sprache.append([z, k, "Deutsch", "A2", "Zertifikat", a1_datum + timedelta(days=R.randint(150, 500)), "telc A2"])
                # offiziell gemeldet? meist ja, manchmal fehlt die Meldung (Geld liegt auf dem Tisch)
                frist = plus_jahre(einreise, 3)
                if a1_datum <= frist and R.random() < 0.85:
                    zielerr.append([z, "Sprache A1", a1_datum + timedelta(days=R.randint(5, 60)), "Stadt Bern",
                                    einreise.year, False])
            else:
                niveau = "A1" if (jahre_hier > 1 and R.random() < 0.25) else "A0"
                sprache.append([z, k, "Deutsch", "A0", "Einschätzung", einreise + timedelta(days=40), "Erstgespräch"])
                if niveau == "A1":
                    # A1 eingeschätzt, aber kein gültiger Nachweis -> Quick Win
                    sprache.append([z, k, "Deutsch", "A1", "Einschätzung", STICHTAG - timedelta(days=R.randint(20, 200)),
                                    "Einschätzung Kursleitung"])

            # ---------- Ausbildung (Ziel 2 über Sek II / Tertiär) ----------
            if 16 <= alter_einreise <= 25 and R.random() < 0.55:
                bs = einreise + timedelta(days=R.randint(200, 500))
                if bs < STICHTAG:
                    be = bs + timedelta(days=330)
                    foerd.append([z, k, bs, be if be < STICHTAG else None, "Brückenangebot",
                                  R.choice(["Berufsvorbereitendes Schuljahr", "Integrationsvorlehre INVOL"]), 28,
                                  "Berufsfachschule Bern", None])
                    if R.random() < (0.35 + 0.35 * alpha):
                        ls = be + timedelta(days=R.randint(20, 120))
                        if ls < STICHTAG:
                            foerd.append([z, k, ls, None, "Sek II",
                                          R.choice(["EBA Logistik", "EBA Küche", "EFZ Detailhandel", "EFZ Fachfrau/-mann Gesundheit"]),
                                          40, R.choice(["gibb Bern", "BFF Bern", "WKS Bern"]), "Lehrvertrag"])
                            if R.random() < 0.85:
                                zielerr.append([z, "Erwerb / Ausbildung", ls + timedelta(days=R.randint(10, 60)),
                                                "Stadt Bern", einreise.year, False])
            elif alter_einreise > 18 and sj >= 12 and R.random() < 0.08:
                ts = einreise + timedelta(days=R.randint(500, 1200))
                if ts < STICHTAG:
                    foerd.append([z, k, ts, None, "Tertiär", "Bachelor (Anerkennung Vorstudium)", 30,
                                  "Universität Bern", None])

            # ---------- Erwerb ----------
            p_job = min(0.85, 0.15 + 0.08 * jahre_hier + 0.2 * alpha)
            if alter_einreise >= 18 and R.random() < p_job:
                von = einreise + timedelta(days=R.randint(200, 1400))
                if von < STICHTAG:
                    bis = von + timedelta(days=R.randint(60, 900))
                    ag, ort = R.choice(ARBEITGEBER)
                    pensum = R.choice([20, 40, 50, 60, 80, 100])
                    lohn = round(pensum / 100 * R.randint(3600, 4800), 2)
                    erwerb.append([z, k, von, bis if bis < STICHTAG else None, ag, ort, pensum, "unselbstständig",
                                   lohn, None, False, R.random() < 0.3, None])
                    zemis_t.append([z, k, von, bis if bis < STICHTAG else None, ag])
                    if pensum >= 60:
                        haushalt_erwerb = True
                        ende = min(bis, STICHTAG)
                        if (ende - von).days >= 183 and R.random() < 0.85:
                            zielerr.append([z, "Erwerb / Ausbildung", von + timedelta(days=183 + R.randint(5, 40)),
                                            "Stadt Bern", einreise.year, False])
                    # Anschlussstelle ohne Unterbruch (teilweise)
                    if bis < STICHTAG and R.random() < 0.3:
                        ag2, ort2 = R.choice(ARBEITGEBER)
                        bis2 = bis + timedelta(days=R.randint(90, 600))
                        erwerb.append([z, k, bis + timedelta(days=1), bis2 if bis2 < STICHTAG else None, ag2, ort2,
                                       R.choice([60, 80, 100]), "unselbstständig", round(R.randint(2800, 4600), 2),
                                       None, False, False, None])
                        zemis_t.append([z, k, bis + timedelta(days=1), bis2 if bis2 < STICHTAG else None, ag2])
                        haushalt_erwerb = True
            # absichtlich: Job in ZEMIS, aber nicht im Erwerb (nicht gemeldete Arbeit)
            if alter_einreise >= 18 and R.random() < 0.04:
                b = zufallsdatum(einreise + timedelta(days=200), STICHTAG - timedelta(days=30))
                zemis_t.append([z, k, b, None, R.choice(TEMP)])

        # ---------- Finanzielle Unterstützung (pro Haushalt) ----------
        if status == "S" or status == "N":
            finanz.append([dossier, "Sozialhilfe", einreise, None, None])
        elif haushalt_erwerb and R.random() < 0.6:
            abl = einreise + timedelta(days=R.randint(500, 1800))
            if abl < STICHTAG:
                finanz.append([dossier, "Sozialhilfe", einreise, abl, R.choice(["Aufnahme einer Erwerbstätigkeit", "Erhöhtes Erwerbseinkommen"])])
                if R.random() < 0.25:
                    # Rückfall: weniger als 12 Monate ohne Sozialhilfe
                    rf = abl + timedelta(days=R.randint(90, 300))
                    if rf < STICHTAG:
                        finanz.append([dossier, "Keine Unterstützung", abl + timedelta(days=1), rf - timedelta(days=1), None])
                        finanz.append([dossier, "Sozialhilfe", rf, None, None])
                    else:
                        finanz.append([dossier, "Keine Unterstützung", abl + timedelta(days=1), None, None])
                else:
                    finanz.append([dossier, "Keine Unterstützung", abl + timedelta(days=1), None, None])
                    if (STICHTAG - abl).days > 380 and R.random() < 0.85:
                        zielerr.append([str(zemis_nr), "Ablösung von der Sozialhilfe", abl + timedelta(days=366),
                                        "Stadt Bern", einreise.year, False])
            else:
                finanz.append([dossier, "Sozialhilfe", einreise, None, None])
        else:
            finanz.append([dossier, "Sozialhilfe", einreise, None, None])

        # ---------- Situationsanalyse-Bericht (Freitext, pro Haushalt) ----------
        if kopf is not None:
            (sa_dir / f"{dossier}.txt").write_text(
                situationsanalyse_text(dossier, kopf["zemis"], land, mutter, groesse,
                                       kopf["alpha"], kopf["sj"], kopf["aj"]),
                encoding="utf-8")

    # ---------- schreiben ----------
    schreiben(ziel / "Hackathon_Klient_Resultat.xlsx",
              ["Klientennummer", "Zemis Nummer", "Dossier-Nr.", "Zuständigkeitsbeginn", "Zuständigkeitsende",
               "Datum Übergang Gemeindezuständigkeit", "Verfahrensstand (aktuell)", "Unterstützung (aktuell)",
               "Fallführung (Sozialarbeiter:in)", "Geburtsdatum", "Geschlecht", "Nationalität Land", "Zivilstand",
               "Muttersprache", "Höchste abgeschlossene Ausbildung", "Schuljahre vor Einreise",
               "Lateinisch alphabetisiert", "Art Analphabetismus", "Jahre Arbeitserfahrung vor Einreise"], klient)
    schreiben(ziel / "Hackathon_Asylgeschäftsdaten_Resultat.xlsx",
              ["Klient/-in Zemis-Nr.", "Klientennummer", "Asylgeschäftsart", "Ereignisdatum", "Erledigung",
               "Erledigungscode", "Erledigungsdatum"], asyl)
    schreiben(ziel / "Hackathon_Asylverfahrensstand_Resultat.xlsx",
              ["Zemis Nummer", "Klientennummer", "Dossier-Nr.", "Verfahrensstand", "Gültig ab", "Gültig bis"], verfahren)
    # Sprachstand absichtlich mit Datum als Text (wie manche Exporte)
    schreiben(ziel / "Hackathon_Sprachstand_Resultat.xlsx",
              ["Klient/-in Zemis-Nr.", "Klientennummer", "Sprache", "Sprachniveau", "Art", "Datum Erreichung",
               "Bemerkungen"], sprache, datum_als_text=True)
    schreiben(ziel / "Hackathon_Integrationsförderung und Ausbildung_Resultat.xlsx",
              ["Klient/-in Zemis-Nr.", "Klientennummer", "Start", "Abschluss", "Art", "Bezeichnung",
               "Stunden pro Woche", "Institution Name", "Bemerkungen"], foerd)
    schreiben(ziel / "Hackathon_Erwerb_Resultat.xlsx",
              ["Klient/-in Zemis-Nr.", "Klientennummer", "Von", "Bis", "Arbeitgeber Name", "Arbeitgeber Ort",
               "Pensum %", "Erwerbsstatus", "Monatseinkommen brutto CHF", "Stundenlohn",
               "Unregelmässiges Einkommen", "Abtretung Sozialdienst", "Bemerkungen"], erwerb)
    schreiben(ziel / "Hackathon_ZEMIS Tätigkeit_Resultat.xlsx",
              ["Zemis Nummer", "Klientennummer", "Arbeitsbeginn", "Verpflichtet bis", "Betrieb"], zemis_t)
    schreiben(ziel / "Hackathon_Finanzielle Unterstützung_Resultat.xlsx",
              ["Dossier-Nr.", "Unterstützung", "Finanzielle Unterstützung Gültig von",
               "Finanzielle Unterstützung Gültig bis", "Hauptgrund Beendigung Unterstützung"], finanz)
    schreiben(ziel / "Hackathon_Dossierperson_Resultat.xlsx",
              ["Dossier-Nr.", "Klientennummer", "Zemis Nummer", "Dossierperson Von", "Dossierperson Bis",
               "Rolle", "Beziehung"], dossierp)
    schreiben(ziel / "Hackathon_Unterbringung_Resultat.xlsx",
              ["Klientennummer", "Von", "Bis", "Unterbringung Art", "PLZ / Ort"], unterbr)
    schreiben(ziel / "Hackathon_Integrationszielerreichung_Resultat.xlsx",
              ["Klient/-in Zemis-Nr.", "Art (Ziel)", "Erreicht am", "Partner (Region)",
               "Jahr Grundgesamtheit (Kohorte)", "Ziel mit Status S erreicht"], zielerr)
    n_berichte = len(list(sa_dir.glob("*.txt")))
    print(f"{personen} Personen, {dossier_nr - 30_000} Haushalte, {n_berichte} Situationsanalyse-Berichte -> {ziel}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--personen", type=int, default=400)
    ap.add_argument("--ziel", default=str(Path(__file__).resolve().parent.parent / "daten" / "demo"))
    a = ap.parse_args()
    erzeugen(a.personen, Path(a.ziel))
