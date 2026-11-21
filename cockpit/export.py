"""Excel out: mehrere Blätter, Kopfzeile fixiert, Filter, Ampel-Farben, Schweizer Datumsformat."""
from io import BytesIO
import re
import pandas as pd
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

FARBEN = {"Erreicht": "C8E6C9", "Auf Kurs": "FFF3C4", "Gefährdet": "F8C9C9",
          "Frist verpasst": "D9D9D9", "Nicht anwendbar": "F2F2F2"}
KOPF = PatternFill("solid", fgColor="1F3A5F")


def excel(blaetter: dict, info: dict | None = None) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        if info:
            pd.DataFrame({"Feld": list(info), "Wert": list(info.values())}).to_excel(xw, sheet_name="Info", index=False)
        for name, df in blaetter.items():
            name = re.sub(r"[\[\]:*?/\\]", "-", name)
            df = df.copy()
            for c in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[c]):
                    df[c] = df[c].dt.date
                elif df[c].dtype == bool or str(df[c].dtype) == "boolean":
                    df[c] = df[c].map({True: "ja", False: "nein"})
            df.to_excel(xw, sheet_name=name[:31], index=False)
            ws = xw.sheets[name[:31]]
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = KOPF
                cell.alignment = Alignment(vertical="center", wrap_text=True)
            for i, col in enumerate(df.columns, start=1):
                breite = max([len(str(col))] + [len(str(v)) for v in df[col].head(200)]) + 2
                ws.column_dimensions[get_column_letter(i)].width = min(55, max(10, breite))
                if str(col).startswith("Quote"):
                    for row in ws.iter_rows(min_row=2, min_col=i, max_col=i):
                        row[0].number_format = "0.0%"
            for row in ws.iter_rows(min_row=2):
                for c in row:
                    if hasattr(c.value, "year") and not isinstance(c.value, str):
                        c.number_format = "DD.MM.YYYY"
            for j, col in enumerate(df.columns, start=1):
                if str(col).startswith("Ziel ") and df[col].astype(str).str.contains("Erreicht|Kurs|Gefährdet|verpasst").any():
                    for row in ws.iter_rows(min_row=2, min_col=j, max_col=j):
                        txt = str(row[0].value or "")
                        for stand, farbe in FARBEN.items():
                            if stand in txt:
                                row[0].fill = PatternFill("solid", fgColor=farbe)
                                break
            if "Ampel" in df.columns:
                j = list(df.columns).index("Ampel") + 1
                for row in ws.iter_rows(min_row=2):
                    txt = str(row[j - 1].value or "")
                    for stand, farbe in FARBEN.items():
                        if stand in txt:
                            for c in row:
                                c.fill = PatternFill("solid", fgColor=farbe)
                            break
        if info:
            ws = xw.sheets["Info"]
            ws.column_dimensions["A"].width = 28
            ws.column_dimensions["B"].width = 80
    return buf.getvalue()
