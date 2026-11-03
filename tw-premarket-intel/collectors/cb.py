"""可轉債：全量入庫（SQLite），溢價率 = CB價 / 轉換價值 - 1，轉換價值 = 股價 / 轉換價 * 100。"""
import logging

from collectors.base import discover, fetch_rows, stock_prices
from core.util import parse_date, pick, stock_code_from_cb, to_float

log = logging.getLogger("cb")

ALIAS = {
    "code": ["債券代碼", "可轉債代碼", "債券代號", "BondCode", "證券代號", "代號", "Code"],
    "name": ["債券簡稱", "債券名稱", "BondName", "名稱", "簡稱", "Name"],
    "price": ["收盤價", "收盤", "成交價", "均價", "ClosingPrice", "Close"],
    "conv_price": ["最新轉換價格", "轉換價格", "轉換價", "ConversionPrice"],
    "volume": ["成交張數", "成交量", "成交數量", "TradeVolume", "Volume"],
    "maturity": ["到期日", "債券到期日", "MaturityDate"],
    "put_date": ["賣回基準日", "賣回權利日", "賣回日", "PutDate"],
    "issue_date": ["上櫃日期", "掛牌日", "發行日期", "發行日", "IssueDate"],
}
NO_FLAG = {"", "N", "n", "否", "0", "-", "--", "無"}


def _normalize(row, fmap):
    out = {k: pick(row, v, fmap.get(k)) for k, v in ALIAS.items()}
    out["call_flag"] = any("贖回" in str(k) and str(v).strip() not in NO_FLAG
                           for k, v in row.items() if "賣回" not in str(k))
    return out


def _sources(ctx):
    cfg = ctx.cfg["cb"]
    if cfg.get("sources"):
        return [(s["site"], s["path"]) for s in cfg["sources"]]
    found = [("tpex", p) for p, _ in discover(ctx, "tpex", ["可轉換公司債", "可轉債", "轉換公司債"])]
    log.info("CB 自動探索到 %d 個端點：%s", len(found), [p for _, p in found])
    return found


def collect(ctx):
    cfg = ctx.cfg["cb"]
    fmap = cfg.get("field_map", {}) or {}
    merged = {}
    errors = []
    for site, path in _sources(ctx):
        try:
            for r in fetch_rows(ctx, site, path):
                n = _normalize(r, fmap)
                code = str(n["code"]).strip() if n["code"] else None
                if not code:
                    continue
                cur = merged.setdefault(code, {"code": code})
                for k, v in n.items():
                    if k != "code" and v not in (None, "") and cur.get(k) in (None, "", False):
                        cur[k] = v
        except Exception as e:
            errors.append(f"{path}: {e}")
    if not merged:
        raise RuntimeError("找不到可用的可轉債端點；請執行 `python main.py --discover 可轉債` 後填入 config.yaml cb.sources。"
                           + (" 錯誤：" + "; ".join(errors) if errors else ""))

    prices = stock_prices(ctx)
    rows = []
    for code, r in merged.items():
        r["price"] = to_float(r.get("price"))
        r["conv_price"] = to_float(r.get("conv_price"))
        r["volume"] = to_float(r.get("volume"))
        for k in ("maturity", "put_date", "issue_date"):
            r[k] = parse_date(r.get(k))
        r["stock_code"] = stock_code_from_cb(code)
        r["stock_price"] = prices.get(r["stock_code"])
        r["premium"] = None
        if r["price"] and r["conv_price"] and r["stock_price"]:
            parity = r["stock_price"] / r["conv_price"] * 100
            r["premium"] = round((r["price"] / parity - 1) * 100, 2)
        rows.append(r)
    ctx.db.save_cb(ctx.today.isoformat(), rows)
    ctx.shared["cb_stock_codes"] = {r["stock_code"] for r in rows}
    return {"rows": rows, "total": len(rows), "with_premium": sum(1 for r in rows if r["premium"] is not None),
            "errors": errors}
