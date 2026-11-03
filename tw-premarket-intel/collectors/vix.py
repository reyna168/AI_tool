"""VIX：抓 ^VIX 日線，計算 5 日變化與歷史百分位，燈號由 analyzers.signals 判定。"""
from analyzers.signals import vix_light
from collectors.base import yahoo_closes


def collect(ctx):
    rows = yahoo_closes(ctx, "^VIX")
    if len(rows) < 2:
        raise RuntimeError("VIX 資料不足")
    ctx.db.upsert_series("VIX", rows)
    hist = [v for _, v in ctx.db.series("VIX")]
    day, close = rows[-1]
    base = rows[-6][1] if len(rows) >= 6 else rows[0][1]
    pct = round(100 * sum(1 for v in hist if v <= close) / len(hist), 1) if len(hist) >= 20 else None
    light, label = vix_light(close, ctx.cfg["vix"])
    return {"date": day, "close": close, "chg5_pct": round((close / base - 1) * 100, 1),
            "percentile": pct, "light": light, "label": label}
