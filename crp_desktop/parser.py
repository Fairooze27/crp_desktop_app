
import re
import json
from collections import OrderedDict
from crp_desktop.resources import IDENTIFIER_MAP

RE_VALUE_NUM = re.compile(r"([-+]?[0-9]*\.?[0-9]+)")
RE_TOKEN_LINE = re.compile(r"^\s*([^\s])\s+(.+)$")
RE_META_DTIME = re.compile(
    r"(\d{2}\/\d{2}\/\d{2,4})\s+(\d{2}h\d{2}mn\d{2}s|\d{2}:\d{2}:\d{2})",
    re.IGNORECASE,
)
RE_NO = re.compile(r"NO\.[:.\s]*([0-9/]+)", re.IGNORECASE)

def keep_printables(s: str) -> str:
    return ''.join(ch if (ch == '\n' or 32 <= ord(ch) <= 126) else ' ' for ch in s)

def find_best_id(text: str) -> str:
    t = text
    m = re.search(r"(?:User\s*ID|UserID|ID)[:.\s]*([A-Za-z][A-Za-z0-9\-_]{1,20})", t, re.IGNORECASE)
    if m:
        cand = m.group(1).strip()
        if not re.fullmatch(r"0+", cand):
            return cand
    m2 = re.search(r"(?:0{2,}|[\x00-\x1f\x7f]{1,})([A-Za-z][A-Za-z0-9\-_]{1,20})", t)
    if m2:
        return m2.group(1)
    header_zone = t[:800]
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-_]{1,20}", header_zone)
    if words:
        measurement_labels = set([
            'WBC','RBC','HGB','HCT','MCV','MCH','MCHC','RDW',
            'PLT','MPV','PCT','PDW','CRP','RESULT','NO','DATE','SID','PID'
        ])
        candidates = [w for w in words if w.upper() not in measurement_labels and not re.fullmatch(r'\d+', w)]
        if candidates:
            return max(candidates, key=len)
    m3 = re.search(r"\b([A-Za-z0-9\-_]{2,15})\b", header_zone)
    if m3:
        return m3.group(1)
    return ""

def extract_header(text: str, out: dict):
    m = RE_NO.search(text)
    if m:
        out['NO.'] = m.group(1).strip()
    mdt = RE_META_DTIME.search(text)
    if mdt:
        out['DATE'] = mdt.group(1).strip()
        t = mdt.group(2)
        t = t.replace('h', ':').replace('mn', ':').replace('s', '')
        out['TIME'] = t
    else:
        m2 = re.search(r"(\d{4}/\d{2}/\d{2})\s+([0-2]?\d:[0-5]\d)", text)
        if m2:
            out['DATE'] = m2.group(1).strip()
            out['TIME'] = m2.group(2).strip()
    msid = re.search(r"\bSID[:.\s]*([0-9A-Za-z\-]+)", text, re.IGNORECASE)
    mpid = re.search(r"\bPID[:.\s]*([0-9A-Za-z\-]+)", text, re.IGNORECASE)
    if msid:
        out['SID'] = msid.group(1).strip()
    if mpid:
        out['PID'] = mpid.group(1).strip()
    mid = re.search(r"(?:User\s*ID|ID)[:.\s]*([A-Za-z0-9\-_]{1,20})", text, re.IGNORECASE)
    if mid and not re.fullmatch(r"0+", mid.group(1).strip()):
        out['ID'] = mid.group(1).strip()
    else:
        candidate = find_best_id(text)
        if candidate:
            out['ID'] = candidate

def extract_fields_from_block(block_text: str) -> dict:
    data = OrderedDict()
    cleaned = keep_printables(block_text.replace('\r\n', '\n').replace('\r', '\n'))
    lines = [ln.strip() for ln in cleaned.split('\n') if ln.strip()]
    footer_map = {}
    extract_header(cleaned, data)
    for line in lines:
        if line.startswith('$'):
            parts = line.split(maxsplit=1)
            footer_map[parts[0]] = parts[1] if len(parts) > 1 else ''
            continue
        m = RE_TOKEN_LINE.match(line)
        if not m:
            data.setdefault('MISC', []).append(line)
            continue
        token, payload = m.group(1), m.group(2).strip()
        if token in IDENTIFIER_MAP:
            label, unit = IDENTIFIER_MAP[token]
            if label == 'ID':
                name_match = re.search(r"([A-Za-z][A-Za-z0-9\-_]{1,20})", payload)
                if name_match:
                    data[label] = name_match.group(1)
                    continue
                val_match = RE_VALUE_NUM.search(payload)
                val = val_match.group(1) if val_match else (payload.split()[0] if payload else '')
                data[label] = val
                continue
            val_match = RE_VALUE_NUM.search(payload)
            val = val_match.group(1) if val_match else (payload.split()[0] if payload else '')
            display = val
            if unit:
                display = f"{display} {unit}"
            if label not in data:
                data[label] = display
        else:
            data[f"TOK:{token}"] = payload
    if ('ID' not in data) or re.fullmatch(r"0+", (data.get('ID') or "").strip()):
        robust = find_best_id(cleaned)
        if robust:
            data['ID'] = robust
    if '$FF' in footer_map:
        data['PacketType'] = footer_map['$FF']
    if '$FB' in footer_map:
        data['InstrumentName'] = footer_map['$FB']
    if '$FE' in footer_map:
        data['FormatVersion'] = footer_map['$FE']
    if '$FD' in footer_map:
        data['Checksum'] = footer_map['$FD']
    return data

# Optional utility to format a receipt-like string (same logic as single-file)
def format_receipt(parsed: dict) -> str:
    lines = []
    lines.append("        RESULT\n")
    no = parsed.get('NO.') or ''
    if no:
        lines.append(f"NO. : {no}")
    dt = (parsed.get('DATE', '') + ' ' + parsed.get('TIME', '')).strip()
    if dt:
        lines.append(dt)
    if 'ID' in parsed:
        lines.append(f"User ID. {parsed['ID']}")
    if 'SID' in parsed:
        lines.append(f"SID. {parsed['SID']}")
    if 'PID' in parsed:
        lines.append(f"PID. {parsed['PID']}")
    lines.append("")
    order = [
        'WBC','RBC','HGB','HCT','MCV','MCH','MCHC','RDW',
        'PLT','MPV','PCT','PDW','%LYM','%MON','%GRA','#LYM','#MON','#GRA','CRP'
    ]
    max_label_len = max(len(x) for x in order)
    for lbl in order:
        val = parsed.get(lbl)
        if val:
            lines.append(f"{lbl.ljust(max_label_len)} : {val}")
    if parsed.get('InstrumentName'):
        lines.append("")
        lines.append(parsed.get('InstrumentName'))
    if parsed.get('FormatVersion'):
        lines.append(f"Format: {parsed.get('FormatVersion')}")
    return "\n".join(lines)
