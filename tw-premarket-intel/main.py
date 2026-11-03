"""台股與宏觀市場每日盤前情報系統

  python main.py --now                 立即執行並推播
  python main.py --now --no-push       只產生本機 .md
  python main.py --now --only vix,cb   只跑指定模組
  python main.py --schedule            常駐，每日 config.schedule_time 自動執行
  python main.py --discover 可轉債     列出 TWSE/TPEx OpenAPI 中符合關鍵字的端點
"""
import argparse
import datetime as dt
import logging
import os
import sys
import time
from zoneinfo import ZoneInfo

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analyzers import report as report_mod
from collectors import base, calendar as cal, cb, ipo, notices, rates, vix
from collectors.base import Ctx
from core.http import Fetcher
from notifiers import markdown, push
from storage.db import DB

log = logging.getLogger("main")
# 順序重要：cb 先跑，notices 才能取得 CB 發行公司代號
MODULES = [("vix", vix), ("rates", rates), ("cb", cb), ("ipo", ipo), ("calendar", cal), ("notices", notices)]


def load_cfg(path="config.yaml"):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def make_ctx(cfg):
    from dotenv import load_dotenv
    load_dotenv()
    db = DB(cfg["db_path"])
    today = dt.datetime.now(ZoneInfo(cfg["timezone"])).date()
    return Ctx(cfg=cfg, db=db, fetcher=Fetcher(db, cfg), today=today)


def run(cfg, do_push=True, only=None):
    ctx = make_ctx(cfg)
    results = {}
    for name, mod in MODULES:
        if only and name not in only:
            continue
        try:
            results[name] = {"ok": True, "data": mod.collect(ctx)}
            log.info("✔ %s", name)
        except Exception as e:           # 單一模組失敗不影響其他模組
            log.warning("✘ %s: %s", name, e)
            results[name] = {"ok": False, "error": str(e)}
    text = markdown.render(report_mod.build(ctx, results))
    path = markdown.save(text, cfg["report_dir"], ctx.today.isoformat())
    log.info("日報已存檔：%s", path)
    if do_push:
        try:
            log.info("推播：%s", push.send(text) or "無")
        except Exception as e:
            log.warning("推播失敗：%s", e)
    return text


def schedule_loop(cfg, do_push):
    tz = ZoneInfo(cfg["timezone"])
    hh, mm = map(int, cfg["schedule_time"].split(":"))
    while True:
        now = dt.datetime.now(tz)
        nxt = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
        if nxt <= now:
            nxt += dt.timedelta(days=1)
        log.info("下次執行：%s", nxt)
        time.sleep((nxt - now).total_seconds())
        try:
            run(cfg, do_push)
        except Exception:
            log.exception("排程執行失敗")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--now", action="store_true")
    ap.add_argument("--schedule", action="store_true")
    ap.add_argument("--no-push", action="store_true")
    ap.add_argument("--only", help="逗號分隔：vix,rates,cb,ipo,calendar,notices")
    ap.add_argument("--discover", metavar="KEYWORD")
    ap.add_argument("--config", default="config.yaml")
    ap.add_argument("-v", "--verbose", action="store_true")
    a = ap.parse_args()
    logging.basicConfig(level=logging.DEBUG if a.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    cfg = load_cfg(a.config)
    if a.discover:
        ctx = make_ctx(cfg)
        for site in ("twse", "tpex"):
            try:
                for p, s in base.discover(ctx, site, a.discover):
                    print(f"[{site}] {p}  {s[:60]}")
            except Exception as e:
                print(f"[{site}] swagger 取得失敗：{e}")
    elif a.schedule:
        schedule_loop(cfg, not a.no_push)
    elif a.now:
        print(run(cfg, not a.no_push, set(a.only.split(",")) if a.only else None))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
