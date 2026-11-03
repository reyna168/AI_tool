"""特別訊息：重大訊息（上市/上櫃）+ 注意股票 + 處置股票，過濾例行公告。"""
import logging

from analyzers.notice_filter import classify
from collectors.base import fetch_rows
from core.util import pick

log = logging.getLogger("notices")

SOURCES = [
    # (來源標籤, site, 已知路徑, swagger 探索關鍵字, 類型)
    ("TWSE重訊", "twse", "/opendata/t187ap04_L", ["每日重大訊息"], "major"),
    ("TPEx重訊", "tpex", "/mopsfin_t187ap04_O", ["每日重大訊息"], "major"),
    ("TWSE注意", "twse", "/announcement/notice", ["注意累計", "注意股票"], "watch"),
    ("TPEx注意", "tpex", "/tpex_trading_warning_information", ["注意", "警示"], "watch"),
    ("TWSE處置", "twse", "/announcement/punish", ["處置"], "disposal"),
    ("TPEx處置", "tpex", "/tpex_disposal_information", ["處置"], "disposal"),
]


def _subject(row):
    s = pick(row, ["主旨", "Subject", "注意交易資訊", "處置原因", "處置條件", "ReasonsOfDisposition"])
    if s:
        return str(s).strip().replace("\n", " ")[:140]
    return " | ".join(str(v) for v in row.values() if v and len(str(v)) > 1)[:140]


def collect(ctx):
    cfg = ctx.cfg["notices"]
    keep_codes = set(map(str, ctx.cfg.get("watchlist") or [])) | set(ctx.shared.get("cb_stock_codes", ()))
    picked, errors, counts = [], [], {}
    for label, site, path, kw, kind in SOURCES:
        try:
            rows = fetch_rows(ctx, site, path, kw)
        except Exception as e:
            errors.append(f"{label}: {e}")
            log.warning("%s failed: %s", label, e)
            continue
        norm = [{"code": str(pick(r, ["公司代號", "證券代號", "股票代號", "SecuritiesCompanyCode", "Code"]) or "").strip(),
                 "name": pick(r, ["公司名稱", "公司簡稱", "證券名稱", "名稱", "CompanyName", "Name"]),
                 "subject": _subject(r), "kind": kind, "source": label} for r in rows]
        counts[label] = len(norm)
        ctx.db.save_announcements(ctx.today.isoformat(), label, norm)
        for n in norm:
            score, tags = classify(n, cfg, keep_codes)
            if score > 0:
                picked.append({**n, "score": score, "tags": tags})
    if not counts:
        raise RuntimeError("; ".join(errors))
    picked.sort(key=lambda x: -x["score"])
    return {"items": picked[: cfg["max_items"]], "total_picked": len(picked), "counts": counts, "errors": errors}
