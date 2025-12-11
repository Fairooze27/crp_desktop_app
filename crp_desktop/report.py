
import base64
import json
from pathlib import Path
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtGui import QTextDocument
from PySide6.QtGui import QPageLayout
from PySide6.QtCore import QMarginsF

# sample test order and display mapping
TEST_ORDER = [
    ("WBC", "WBC"), ("RBC", "RBC"), ("HGB", "HGB"), ("HCT", "HCT"),
    ("MCV", "MCV"), ("MCH", "MCH"), ("MCHC", "MCHC"), ("RDW", "RDW"),
    ("PLT", "PLT"), ("MPV", "MPV"), ("PCT", "PCT"), ("PDW", "PDW"),
    ("%LYM", "%LYM"), ("%MON", "%MON"), ("%GRA", "%GRA"),
    ("#LYM", "#LYM"), ("#MON", "#MON"), ("#GRA", "#GRA"),
    ("CRP", "CRP")
]

def _img_to_base64(path: str) -> str:
    """Return data URI for an image file, or empty string if not found."""
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    b = p.read_bytes()
    mime = "image/png" if p.suffix.lower() in (".png",) else "image/jpeg"
    return f"data:{mime};base64," + base64.b64encode(b).decode("ascii")

def generate_report_html(parsed: dict, settings: dict = None, logo_path: str = None) -> str:
    """
    Build an HTML report string using the parsed result dict and optional settings.
    parsed: dict from extract_fields_from_block or DB row (parsed fields)
    settings: dictionary with clinic_name, report_title, footer_text, etc.
    """
    settings = settings or {}
    clinic = settings.get("clinic_name", "Your Clinic Name")
    title = settings.get("report_title", "LAB REPORT")
    footer = settings.get("footer_text", "")
    logo_data_uri = _img_to_base64(logo_path) if logo_path else ""

    # build patient info
    pid = parsed.get("ID") or parsed.get("patient_id") or parsed.get("patient_id", "")
    instrument = parsed.get("InstrumentName") or parsed.get("instrument_no") or ""
    measure_dt = parsed.get("DATE", "") + (" " + parsed.get("TIME") if parsed.get("TIME") else "")
    measure_dt = measure_dt.strip() or parsed.get("measure_datetime") or parsed.get("created_at") or ""

    # Start HTML
    html = f"""
    <html>
    <head>
    <meta charset="utf-8"/>
    <style>
      body {{ font-family: Arial, Helvetica, sans-serif; font-size: 12pt; color: #111; margin: 20px; }}
      .header {{ display:flex; align-items:center; border-bottom: 2px solid #333; padding-bottom:8px; margin-bottom:12px; }}
      .logo {{ width: 120px; }}
      .clinic {{ flex:1; text-align:left; padding-left:12px; }}
      .clinic h1 {{ margin:0; font-size:18pt; }}
      .clinic p {{ margin:0; font-size:10pt; color:#333; }}
      .title {{ text-align:center; font-weight:bold; margin-top:10px; margin-bottom:8px; font-size:13pt; }}
      .patient-box {{ border:1px solid #bbb; padding:10px; margin-bottom:12px; }}
      .patient-row {{ display:flex; justify-content:space-between; padding:2px 0; }}
      .patient-label {{ width:140px; color:#333; font-weight:600; }}
      table.results {{ width:100%; border-collapse: collapse; margin-top:8px; }}
      table.results th, table.results td {{ border:1px solid #bbb; padding:6px 8px; text-align:left; font-size:11pt; }}
      table.results th {{ background:#f3f3f3; font-weight:700; }}
      .footer {{ margin-top:18px; font-size:9pt; color:#333; border-top:1px solid #ddd; padding-top:8px; }}
      .sig {{ margin-top:26px; display:flex; justify-content:space-between; align-items:center; }}
      .sig .right {{ text-align:center; }}
      .page-break {{ page-break-after: always; }}
    </style>
    </head>
    <body>
      <div class="header">
    """

    if logo_data_uri:
        html += f'<div class="logo"><img src="{logo_data_uri}" style="max-width:120px;max-height:80px;"></div>'
    html += f"""
        <div class="clinic">
          <h1>{clinic}</h1>
          <p>{settings.get("clinic_address","")}</p>
          <p style="font-size:10pt;color:#666;">{settings.get("clinic_contact","")}</p>
        </div>
      </div>

      <div class="title">{title}</div>

      <div class="patient-box">
        <div class="patient-row"><div><span class="patient-label">Patient ID:</span> {pid}</div><div><span class="patient-label">Instrument:</span> {instrument}</div></div>
        <div class="patient-row"><div><span class="patient-label">Date / Time:</span> {measure_dt}</div><div><span class="patient-label">SID / PID:</span> {parsed.get('SID','')} {parsed.get('PID','')}</div></div>
      </div>

      <table class="results">
        <thead>
          <tr>
            <th style="width:40%;">Test Name</th>
            <th style="width:20%;">Result</th>
            <th style="width:15%;">Reference Range</th>
            <th style="width:10%;">Units</th>
            <th style="width:15%;">Method</th>
          </tr>
        </thead>
        <tbody>
    """

    # produce rows from TEST_ORDER (uses mapping to units if parsed had units)
    for key, display in TEST_ORDER:
        val = parsed.get(display) or parsed.get(key) or ""
        if not val:
            continue
        # split value/unit if it already contains unit (e.g. "6.3 10^3/uL")
        # crude parse: last token that contains '/' or '^' or letters => unit; otherwise empty
        result_text = str(val)
        unit = ""
        ref = parsed.get(f"{display}_ref", "") or ""
        # some of your parsed fields already contain unit, leave as-is in result column
        html += f"<tr><td>{display}</td><td>{result_text}</td><td>{ref}</td><td>{parsed.get('unit_'+display,'')}</td><td></td></tr>"

    # include misc lines (MISC) if present - show below table
    html += "</tbody></table>"

    misc = parsed.get("MISC")
    if misc:
        if isinstance(misc, list):
            misc_text = "<br/>".join(misc)
        else:
            misc_text = str(misc)
        html += f"<div style='margin-top:10px; font-size:10pt; color:#333;'><b>Notes:</b><div>{misc_text}</div></div>"

    html += f"""
      <div class="sig">
         <div class="left"></div>
         <div class="right">
             <div>Authorized by</div>
             <div style="margin-top:36px;">(Signature)</div>
         </div>
      </div>

      <div class="footer">{footer}</div>

    </body></html>
    """

    return html

def save_html_to_pdf(html: str, out_path: str) -> None:
    """
    Convert HTML string to PDF using Qt's QTextDocument + QPrinter.
    """
    doc = QTextDocument()
    doc.setHtml(html)

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(out_path)
    # optional: set page margins (in mm) - compatible signature for Qt6/PySide6
    try:
        printer.setPageMargins(QMarginsF(15, 15, 15, 15), QPageLayout.Millimeter)
    except Exception:
        try:
            printer.setPageMargins(15, 15, 15, 15, QPrinter.Millimeter)
        except Exception:
            pass

    # PySide6 may expose this as print_ instead of print depending on version
    try:
        doc.print(printer)      # type: ignore[attr-defined]
    except AttributeError:
        doc.print_(printer)
