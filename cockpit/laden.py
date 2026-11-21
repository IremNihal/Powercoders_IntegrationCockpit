"""Excel-Exporte einlesen: Tabelle erkennen, Spalten zuordnen, Schweizer Daten lesen."""
from dataclasses import dataclass, field
from pathlib import Path
import pandas as pd

from .schema import TABELLEN, norm, tabelle_aus_dateiname


@dataclass
class Ladebericht:
    tabelle: str
    datei: str
    zeilen: int = 0
    erkannt: list = field(default_factory=list)
    fehlend_pflicht: list = field(default_factory=list)
    unbekannt: list = field(default_factory=list)


def datum(serie: pd.Series) -> pd.Series:
    """Liest echte Excel-Daten, '31.12.2025', '2025-12-31' und Excel-Seriennummern."""
    if pd.api.types.is_datetime64_any_dtype(serie):
        return serie.dt.normalize()
    s = serie.copy()
    num = pd.to_numeric(s, errors="coerce")
    seriell = num.between(10000, 80000)
    out = pd.to_datetime(s.where(~seriell).astype("string"), dayfirst=True, errors="coerce", format="mixed")
    if seriell.any():
        out = out.where(~seriell, pd.to_datetime("1899-12-30") + pd.to_timedelta(num.where(seriell), unit="D"))
    return out.dt.normalize()


def spalten_zuordnen(df: pd.DataFrame, key: str):
    spec = TABELLEN[key]["spalten"]
    vorhanden = {norm(c): c for c in df.columns}
    mapping, erkannt = {}, []
    # 1) exakte Treffer
    for intern, aliase in spec.items():
        for a in aliase:
            if norm(a) in vorhanden and vorhanden[norm(a)] not in mapping:
                mapping[vorhanden[norm(a)]] = intern
                erkannt.append(intern)
                break
    # 2) Spaltenname beginnt mit Alias, z.B. 'Sprachniveau (A0 … C2)'
    for intern, aliase in spec.items():
        if intern in erkannt:
            continue
        for a in aliase:
            treffer = [orig for n, orig in vorhanden.items() if n.startswith(norm(a)) and orig not in mapping]
            if treffer:
                mapping[treffer[0]] = intern
                erkannt.append(intern)
                break
    unbekannt = [c for c in df.columns if c not in mapping]
    return mapping, erkannt, unbekannt


def tabelle_lesen(quelle, dateiname: str, key: str | None = None):
    key = key or tabelle_aus_dateiname(dateiname)
    if key is None:
        return None, None
    roh = pd.read_excel(quelle, sheet_name=0, dtype=object)
    roh = roh.dropna(how="all")
    mapping, erkannt, unbekannt = spalten_zuordnen(roh, key)
    df = roh.rename(columns=mapping)[[c for c in mapping.values()]]
    spec = TABELLEN[key]
    for intern in spec["spalten"]:
        if intern not in df.columns:
            df[intern] = pd.NA
    for c in spec["datum"]:
        df[c] = datum(df[c])
    for c in ("zemis", "klientennr"):
        if c in df.columns:
            df[c] = df[c].astype("string").str.replace(r"\.0$", "", regex=True).str.strip()
    if "dossier" in df.columns:
        df["dossier"] = df["dossier"].astype("string").str.strip()
    bericht = Ladebericht(
        tabelle=key, datei=dateiname, zeilen=len(df), erkannt=erkannt,
        fehlend_pflicht=[p for p in spec["pflicht"] if p not in erkannt], unbekannt=unbekannt,
    )
    return df, bericht


def ordner_lesen(ordner: Path):
    daten, berichte = {}, []
    for f in sorted(Path(ordner).glob("*.xlsx")):
        if f.name.startswith("~$"):
            continue
        df, b = tabelle_lesen(f, f.name)
        if df is None:
            continue
        daten[b.tabelle] = df
        berichte.append(b)
    for key, spec in TABELLEN.items():
        if key not in daten:
            daten[key] = pd.DataFrame(columns=list(spec["spalten"].keys()))
    return daten, berichte
