"""Fed 利率（FRED DFF）、美 10Y（FRED DGS10，備援 ^TNX）、台灣利率（config 手動維護）。"""
import csv
import io
import logging

from analyzers.signals import spread_view
from collectors.base import yahoo_closes

log = logging.getLogger("rates")


def fred(ctx, series_id, keep=400):
    text = ctx.fetcher.get_text("https://fred.stlouisfed.org/graph/fredgraph.csv", params={"id": series_id})
    out = []
    for r in csv.DictReader(io.StringIO(text)):
        vals = list(r.values())
        try:
            out.append((vals[0], float(vals[1])))
        except (ValueError, IndexError):
            continue
    if not out:
        raise RuntimeError(f"FRED {series_id} 無資料")
    return out[-keep:]


def collect(ctx):
    fed = fred(ctx, "DFF")
    ctx.db.upsert_series("FED_FUNDS", fed)
    try:
        us10 = fred(ctx, "DGS10")
    except Exception as e:
        log.warning("FRED DGS10 failed (%s), fallback ^TNX", e)
        us10 = yahoo_closes(ctx, "^TNX", "3mo")
    ctx.db.upsert_series("US10Y", us10)

    tw = ctx.cfg.get("tw_rates", {}) or {}
    result = {"fed_funds": fed[-1][1], "fed_date": fed[-1][0],
              "us10y": us10[-1][1], "us10y_date": us10[-1][0],
              "tw_discount": tw.get("discount_rate"), "tw_10y": tw.get("cgb_10y"),
              "tw_as_of": tw.get("as_of"), "warnings": []}
    if tw.get("cgb_10y") is None or tw.get("discount_rate") is None:
        result["warnings"].append("config.yaml 的 tw_rates 尚未填寫，利差相關欄位無法計算")
    if tw.get("cgb_10y") is not None:
        spread = round(us10[-1][1] - float(tw["cgb_10y"]), 3)
        ctx.db.upsert_series("SPREAD_US_TW_10Y", [(ctx.today.isoformat(), spread)])
        result["spread_10y"] = spread
        result["spread_view"] = spread_view(spread, ctx.db.series("SPREAD_US_TW_10Y"), ctx.today)
    if tw.get("discount_rate") is not None:
        result["fed_vs_discount"] = round(fed[-1][1] - float(tw["discount_rate"]), 3)
    return result
