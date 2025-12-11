
import sqlite3
import json
from datetime import datetime
from crp_desktop.resources import DB_PATH

def get_db(path: str = DB_PATH):
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db(path: str = DB_PATH):
    conn = sqlite3.connect(path)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS crp_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            instrument_no TEXT,
            date TEXT,
            time TEXT,
            measure_datetime TEXT,
            patient_id TEXT,
            sid TEXT,
            pid TEXT,
            wbc TEXT,
            rbc TEXT,
            hgb TEXT,
            hct TEXT,
            mcv TEXT,
            mch TEXT,
            mchc TEXT,
            rdw TEXT,
            plt TEXT,
            mpv TEXT,
            pct TEXT,
            pdw TEXT,
            pct_lym TEXT,
            pct_mon TEXT,
            pct_gra TEXT,
            hash_lym TEXT,
            hash_mon TEXT,
            hash_gra TEXT,
            crp TEXT,
            instrument_name TEXT,
            format_version TEXT,
            checksum TEXT,
            packet_type TEXT,
            misc TEXT,
            raw_payload TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
        """
    )
    conn.commit()
    conn.close()

def _safe_get(parsed: dict, key: str):
    val = parsed.get(key)
    if isinstance(val, list):
        return "\n".join(val)
    return val

def save_result(parsed: dict, conn: sqlite3.Connection = None):
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True
    cur = conn.cursor()
    date_str = parsed.get('DATE')
    time_str = parsed.get('TIME')
    measure_dt = None
    if date_str and time_str:
        try:
            year_part = date_str.split('/')[-1]
            if len(year_part) == 2:
                dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%y %H:%M:%S")
            else:
                dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")
            measure_dt = dt.isoformat(sep=' ')
        except Exception:
            try:
                t = time_str.replace('h', ':').replace('mn', ':').replace('s', '')
                year_part = date_str.split('/')[-1]
                if len(year_part) == 2:
                    dt = datetime.strptime(f"{date_str} {t}", "%d/%m/%y %H:%M:%S")
                else:
                    dt = datetime.strptime(f"{date_str} {t}", "%d/%m/%Y %H:%M:%S")
                measure_dt = dt.isoformat(sep=' ')
            except Exception:
                measure_dt = f"{date_str} {time_str}"
    row = {
        "instrument_no": parsed.get("NO."),
        "date": date_str,
        "time": time_str,
        "measure_datetime": measure_dt,
        "patient_id": parsed.get("ID"),
        "sid": parsed.get("SID"),
        "pid": parsed.get("PID"),
        "wbc": parsed.get("WBC"),
        "rbc": parsed.get("RBC"),
        "hgb": parsed.get("HGB"),
        "hct": parsed.get("HCT"),
        "mcv": parsed.get("MCV"),
        "mch": parsed.get("MCH"),
        "mchc": parsed.get("MCHC"),
        "rdw": parsed.get("RDW"),
        "plt": parsed.get("PLT"),
        "mpv": parsed.get("MPV"),
        "pct": parsed.get("PCT"),
        "pdw": parsed.get("PDW"),
        "pct_lym": parsed.get("%LYM"),
        "pct_mon": parsed.get("%MON"),
        "pct_gra": parsed.get("%GRA"),
        "hash_lym": parsed.get("#LYM"),
        "hash_mon": parsed.get("#MON"),
        "hash_gra": parsed.get("#GRA"),
        "crp": parsed.get("CRP"),
        "instrument_name": parsed.get("InstrumentName"),
        "format_version": parsed.get("FormatVersion"),
        "checksum": parsed.get("Checksum"),
        "packet_type": parsed.get("PacketType"),
        "misc": _safe_get(parsed, "MISC"),
        "raw_payload": json.dumps(parsed, ensure_ascii=False),
    }
    cur.execute(
        """
        INSERT INTO crp_results (
            instrument_no,date,time,measure_datetime,patient_id,sid,pid,
            wbc,rbc,hgb,hct,mcv,mch,mchc,rdw,plt,mpv,pct,pdw,
            pct_lym,pct_mon,pct_gra,hash_lym,hash_mon,hash_gra,crp,
            instrument_name,format_version,checksum,packet_type,misc,raw_payload
        ) VALUES (
            :instrument_no,:date,:time,:measure_datetime,:patient_id,:sid,:pid,
            :wbc,:rbc,:hgb,:hct,:mcv,:mch,:mchc,:rdw,:plt,:mpv,:pct,:pdw,
            :pct_lym,:pct_mon,:pct_gra,:hash_lym,:hash_mon,:hash_gra,:crp,
            :instrument_name,:format_version,:checksum,:packet_type,:misc,:raw_payload
        )
        """,
        row,
    )
    conn.commit()
    if close_conn:
        conn.close()

def get_settings(conn: sqlite3.Connection = None) -> dict:
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True
    cur = conn.cursor()
    cur.execute("SELECT key,value FROM settings")
    rows = cur.fetchall()
    data = {r["key"]: r["value"] for r in rows}
    data.setdefault("clinic_name", "Your Clinic Name")
    data.setdefault("report_title", "CRP & CBC REPORT")
    data.setdefault("footer_text", "This report is for clinical use only.")
    if close_conn:
        conn.close()
    return data

def set_settings(data: dict, conn: sqlite3.Connection = None):
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True
    cur = conn.cursor()
    for k, v in data.items():
        cur.execute(
            """
            INSERT INTO settings (key,value) VALUES (?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """, (k, v)
        )
    conn.commit()
    if close_conn:
        conn.close()
