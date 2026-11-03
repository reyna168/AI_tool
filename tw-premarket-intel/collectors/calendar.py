"""未來 N 天的除權息與法說會。TWSE 除權息預告表 + TPEx/TWSE OpenAPI（swagger 探索）。"""
import datetime as dt
import json
import logging

from analyzers.signals import ex_yield
from collectors.base import fetch_rows
from core.util import parse_date, pick, to_float

log = logging.getLogger("calendar")
TWT48U = "https://www.twse.com.tw/exchangeReport/TWT48U"


def _ok(text):
    try:
        return json.loads(text).get("stat") == "OK"
    except Exception:
        return False


def _twse_exdiv(ctx, start, end):
    j = json.loads(ctx.fetcher.get_text(
        TWT48U, params={"response": "json", "strDate": start.strftime("%Y%m%d"),
                        "endDate": end.strftime("%Y%m%d")}, validator=_ok))
    f = j["fields"]
    idx = lambda name: next(i for i, x in enumerate(f) if name in x)
    i_date, i_code, i_name = idx("資料日期"), idx("股票代號"), idx("名稱")
    i_prev, i_div, i_kind = idx("除權息前收盤價"), idx("權值+息值"), idx("權/息")
    out = []
    for r in j["data"]:
        out.append({"date": parse_date(r[i_date]), "code": str(r[i_code]).strip(), "name": r[i_name],
                    "market": "上市", "kind": r[i_kind], "dividend": to_float(r[i_div]),
                    "prev_close": to_float(r[i_prev])})
    return out


def _openapi_exdiv(ctx, site, label):
    out = []
    for r in fetch_rows(ctx, site, None, ["除權息", "除息"]):
        d = parse_date(pick(r, ["除權息日期", "除息日", "除權息日", "Date"]))
        code = pick(r, ["股票代號", "代號", "SecuritiesCompanyCode", "Code"])
        if not d or not code:
            continue
        out.append({"date": d, "code": str(code).strip(), "name": pick(r, ["股票名稱", "名稱", "公司名稱", "Name"]),
                    "market": label, "kind": pick(r, ["權/息", "類別"]) or "",
                    "dividend": to_float(pick(r, ["權值+息值", "現金股利", "每股現金股利", "除息金額"])),
                    "prev_close": to_float(pick(r, ["除權息前收盤價", "前收盤價"]))})
    return out


def _conferences(ctx, start, end):
    out, errs = [], []
    for site, label in (("twse", "上市"), ("tpex", "上櫃")):
        try:
            for r in fetch_rows(ctx, site, None, ["法人說明會", "法說會"]):
                d = parse_date(pick(r, ["召開法人說明會日期", "法說會日期", "召開日期", "舉行日期", "日期"]))
                code = pick(r, ["公司代號", "股票代號", "SecuritiesCompanyCode", "Code"])
                if d and code and start <= d <= end:
                    out.append({"date": d, "code": str(code).strip(), "market": label,
                                "name": pick(r, ["公司名稱", "公司簡稱", "名稱", "CompanyName", "Name"]),
                                "detail": {"place": pick(r, ["召開法人說明會地點", "地點"])}})
        except Exception as e:
            errs.append(f"{label}法說: {e}")
    return out, errs


def collect(ctx):
    start, end = ctx.today, ctx.today + dt.timedelta(days=ctx.cfg["window_days"])
    errors, ex = [], []
    for fn, args in ((_twse_exdiv, (ctx, start, end)), (_openapi_exdiv, (ctx, "tpex", "上櫃"))):
        try:
            ex += fn(*args)
        except Exception as e:
            errors.append(f"除權息({fn.__name__}): {e}")
            log.warning("exdiv source failed: %s", e)
    ex = [e for e in ex if e["date"] and start <= e["date"] <= end]
    for e in ex:
        e["yield_pct"] = ex_yield(e["dividend"], e["prev_close"])
        e["high_yield"] = (e["yield_pct"] or 0) >= ctx.cfg["yield_threshold"]
    ex.sort(key=lambda e: (e["date"], -(e["yield_pct"] or 0)))
    ctx.db.save_events("exdiv", [{**e, "detail": {k: v for k, v in e.items() if k not in ("date", "code", "name")}}
                                 for e in ex])
    conf, cerr = _conferences(ctx, start, end)
    errors += cerr
    conf.sort(key=lambda e: e["date"])
    ctx.db.save_events("conference", conf)
    if not ex and not conf and errors:
        raise RuntimeError("; ".join(errors))
    return {"exdiv": ex, "conferences": conf, "errors": errors}
