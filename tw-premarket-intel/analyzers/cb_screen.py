"""可轉債四類精選：低溢價/負溢價、百元以下防守、到期/賣回/贖回、新發行。"""
from core.util import days_until


def _pct_rank(hist, cur):
    return round(100 * sum(1 for h in hist if h <= cur) / len(hist)) if len(hist) >= 20 else None


def screen(rows, cfg, today, db=None):
    c = cfg["cb"]
    n = c["max_items"]
    picks = {"discount": [], "defensive": [], "event": [], "new": []}
    for r in rows:
        prem, price = r.get("premium"), r.get("price")
        tags = []
        if prem is not None and prem < c["premium_max"]:
            tags.append("discount")
            if db is not None:
                r["premium_pct_rank"] = _pct_rank(db.premium_history(r["code"]), prem)
        if price and price <= c["low_price"] and (r.get("volume") or 0) >= c["min_volume"]:
            tags.append("defensive")
        dm, dp = days_until(r.get("maturity"), today), days_until(r.get("put_date"), today)
        ev = []
        if dm is not None and 0 <= dm <= c["maturity_days"]:
            ev.append(f"{dm}天後到期")
        if dp is not None and 0 <= dp <= c["put_days"]:
            ev.append(f"{dp}天後賣回")
        if r.get("call_flag"):
            ev.append("贖回條款")
        if ev:
            tags.append("event"); r["event_note"] = "、".join(ev)
        di = days_until(r.get("issue_date"), today)
        if di is not None and -c["new_days"] <= di <= c["new_days"]:
            tags.append("new")
        for t in tags:
            picks[t].append(r)
    picks["discount"].sort(key=lambda r: r["premium"])
    picks["defensive"].sort(key=lambda r: -(r.get("volume") or 0))
    picks["event"].sort(key=lambda r: r.get("event_note", ""))
    return {k: v[:n] for k, v in picks.items()}, {k: len(v) for k, v in picks.items()}
