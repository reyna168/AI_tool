"""共用工具：日期解析（含民國年）、數字解析、欄位別名比對。"""
import datetime as dt
import re


def parse_date(s):
    """支援 2026/01/05、115/01/05、115年01月05日、20260105、1150105、2026-01-05。"""
    if s is None:
        return None
    if isinstance(s, dt.datetime):
        return s.date()
    if isinstance(s, dt.date):
        return s
    s = str(s).strip()
    if not s:
        return None
    m = re.match(r"^(\d{2,4})[/\-.年](\d{1,2})[/\-.月](\d{1,2})", s)
    if m:
        y, mo, d = int(m[1]), int(m[2]), int(m[3])
    elif re.match(r"^\d{8}$", s):
        y, mo, d = int(s[:4]), int(s[4:6]), int(s[6:])
    elif re.match(r"^\d{7}$", s):
        y, mo, d = int(s[:3]), int(s[3:5]), int(s[5:])
    else:
        return None
    if y < 1911:
        y += 1911
    try:
        return dt.date(y, mo, d)
    except ValueError:
        return None


def to_float(v):
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("%", "")
    if s in ("", "-", "--", "---", "N/A", "X"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def pick(row, aliases, field_override=None):
    """從 dict row 以別名取值：先精確比對，再包含比對。field_override 為明確欄位名。"""
    if field_override and field_override in row:
        return row[field_override]
    for a in aliases:
        if a in row:
            return row[a]
    for a in aliases:
        if len(a) < 3:
            continue
        for k in row:
            if a in str(k):
                return row[k]
    return None


def days_until(d, today):
    return None if d is None else (d - today).days


def stock_code_from_cb(code):
    code = str(code).strip()
    if len(code) >= 5:
        return code[:-1]
    return code
