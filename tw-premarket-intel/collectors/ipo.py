"""即將掛牌/申購的新股：TWSE「公開申購配售彙總表」（涵蓋上市與上櫃）。"""
import datetime as dt
import json

from core.util import parse_date, to_float

URL = "https://www.twse.com.tw/rwd/zh/announcement/publicForm"


def _ok(text):
    try:
        return json.loads(text).get("stat") == "OK"
    except Exception:
        return False


def _col(fields, *names):
    for n in names:
        for i, f in enumerate(fields):
            if n in f:
                return i
    return None


def collect(ctx):
    j = json.loads(ctx.fetcher.get_text(URL, params={"response": "json"}, validator=_ok))
    fields, data = j["fields"], j["data"]
    ix = {k: _col(fields, *v) for k, v in {
        "draw": ("抽籤日期",), "start": ("申購開始日",), "end": ("申購結束日",),
        "list": ("撥券日期", "上市", "上櫃日期"), "code": ("證券代號",), "name": ("證券名稱",),
        "market": ("發行市場",), "price": ("實際承銷價", "承銷價"), "rate": ("中籤率",),
    }.items()}
    end = ctx.today + dt.timedelta(days=ctx.cfg["window_days"])
    out = []
    for row in data:
        g = lambda k: row[ix[k]] if ix.get(k) is not None else None
        dates = {k: parse_date(g(k)) for k in ("draw", "start", "end", "list")}
        key_dates = [d for d in dates.values() if d and ctx.today <= d <= end]
        if not key_dates:
            continue
        out.append({"date": min(key_dates), "code": str(g("code")).strip(), "name": g("name"),
                    "detail": {"market": g("market"), "price": to_float(g("price")), "rate": g("rate"),
                               **{k: (v.isoformat() if v else None) for k, v in dates.items()}}})
    out.sort(key=lambda r: r["date"])
    ctx.db.save_events("ipo", out)
    return {"items": out}
