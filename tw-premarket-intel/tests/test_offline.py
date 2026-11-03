"""離線測試：不連網，用假 Fetcher 驗證解析、篩選、渲染與容錯。 python -m unittest discover tests"""
import datetime as dt
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yaml
from analyzers import report as report_mod
from analyzers.signals import ex_yield, spread_view, vix_light
from analyzers.notice_filter import classify
from collectors import base, calendar as cal, cb, ipo, notices, rates, vix
from collectors.base import Ctx
from core.http import Fetcher
from core.util import parse_date, pick, stock_code_from_cb, to_float
from notifiers import markdown
from storage.db import DB

TODAY = dt.date(2026, 11, 3)
CFG = yaml.safe_load(open(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml"), encoding="utf-8"))
CFG["tw_rates"] = {"discount_rate": 2.0, "cgb_10y": 1.6, "as_of": "test"}
CFG["watchlist"] = ["2330"]


class FakeFetcher:
    def __init__(self, routes): self.routes = routes
    def _find(self, url):
        for k, v in self.routes.items():
            if k in url:
                if isinstance(v, Exception): raise v
                return v
        raise RuntimeError("no route " + url)
    def get_json(self, url, params=None, **kw):
        v = self._find(url); return v if not isinstance(v, str) else json.loads(v)
    def get_text(self, url, params=None, **kw):
        v = self._find(url); return v if isinstance(v, str) else json.dumps(v)


def make_ctx(routes):
    d = tempfile.mkdtemp()
    return Ctx(cfg=CFG, db=DB(os.path.join(d, "t.db")), fetcher=FakeFetcher(routes), today=TODAY)


def yahoo(closes):
    ts = [int(dt.datetime(2026, 10, 1 + i, 14, 30, tzinfo=dt.timezone.utc).timestamp()) for i in range(len(closes))]
    return {"chart": {"result": [{"timestamp": ts, "indicators": {"quote": [{"close": closes}]}}]}}


class Utils(unittest.TestCase):
    def test_dates(self):
        for s in ("2026/11/05", "115/11/05", "115年11月05日", "20261105", "1151105", "2026-11-05"):
            self.assertEqual(parse_date(s), dt.date(2026, 11, 5), s)
        self.assertIsNone(parse_date("abc"))
    def test_nums(self):
        self.assertEqual(to_float("1,234.5"), 1234.5); self.assertIsNone(to_float("--"))
    def test_cb_code(self):
        self.assertEqual(stock_code_from_cb("23301"), "2330")
    def test_pick(self):
        self.assertEqual(pick({"債券名稱": "A"}, ["債券名稱", "名稱"]), "A")
        self.assertIsNone(pick({"股票代號": "1"}, ["代號"]))  # 2 字別名不做模糊比對，避免誤中
        self.assertEqual(pick({"x": 1, "債券代碼": "9"}, ["債券代碼"], "x"), 1)
    def test_vix_light(self):
        c = CFG["vix"]
        self.assertEqual([vix_light(v, c)[0] for v in (12, 20, 30, 40)], ["🟢", "⚪", "🟡", "🔴"])
    def test_yield_spread(self):
        self.assertEqual(ex_yield(6, 100), 6.0); self.assertIsNone(ex_yield(None, 100))
        self.assertIn("擴大", spread_view(0.5, [("2026-10-20", 0.2)], TODAY))


class Cache(unittest.TestCase):
    def test_db_cache_and_history(self):
        db = DB(os.path.join(tempfile.mkdtemp(), "c.db"))
        db.cache_put("k", "2026-11-03", "body")
        self.assertEqual(db.cache_get("k", "2026-11-03"), "body"); self.assertIsNone(db.cache_get("k", "2026-11-02"))
        db.upsert_series("S", [("2026-11-01", 1.0), ("2026-11-02", 2.0)])
        self.assertEqual(db.series("S", 1), [("2026-11-02", 2.0)])


class Collectors(unittest.TestCase):
    def test_vix(self):
        ctx = make_ctx({"finance/chart": yahoo([14, 15, 16, 17, 18, 19, 38.0])})
        r = vix.collect(ctx)
        self.assertEqual(r["light"], "🔴"); self.assertAlmostEqual(r["chg5_pct"], round((38 / 15 - 1) * 100, 1))

    def test_rates(self):
        csv_ = lambda col: "observation_date," + col + "\n2026-10-30,4.0\n2026-11-02,4.1\n2026-11-03,.\n"
        ctx = make_ctx({"fredgraph": csv_("X")})
        r = rates.collect(ctx)
        self.assertEqual(r["us10y"], 4.1); self.assertAlmostEqual(r["spread_10y"], 2.5)

    def test_cb_and_screen(self):
        cbrows = [{"債券代碼": "23301", "債券簡稱": "台積轉", "收盤價": "100", "轉換價格": "500", "成交張數": "300",
                   "到期日": "115/12/01"},
                  {"債券代碼": "34561", "債券簡稱": "新發債", "收盤價": "98", "轉換價格": "50", "成交張數": "80",
                   "上櫃日期": "20261101"}]
        stocks_twse = [{"Code": "2330", "ClosingPrice": "520"}]
        stocks_tpex = [{"SecuritiesCompanyCode": "3456", "Close": "40"}]
        ctx = make_ctx({"swagger": {"paths": {"/v1/bond_cb": {"get": {"summary": "可轉換公司債資料"}}}},
                        "/v1/bond_cb": cbrows, "STOCK_DAY_ALL": stocks_twse, "tpex_mainboard": stocks_tpex})
        r = cb.collect(ctx)
        self.assertEqual(r["total"], 2)
        a = next(x for x in r["rows"] if x["code"] == "23301")
        self.assertAlmostEqual(a["premium"], round((100 / (520 / 500 * 100) - 1) * 100, 2))  # 負溢價
        rep = report_mod.build(ctx, {"cb": {"ok": True, "data": r}})
        picks = rep["sections"]["cb"]["picks"]
        self.assertIn("23301", [x["code"] for x in picks["discount"]])
        self.assertIn("23301", [x["code"] for x in picks["event"]])
        self.assertIn("34561", [x["code"] for x in picks["new"]])
        self.assertIn("34561", [x["code"] for x in picks["defensive"]])
        self.assertIn("2330", ctx.shared["cb_stock_codes"])

    def test_ipo(self):
        j = {"stat": "OK", "fields": ["序號", "抽籤日期", "證券名稱", "證券代號", "發行市場", "申購開始日", "申購結束日",
                                      "實際承銷價(元)", "撥券日期(上市、上櫃日期)", "中籤率(%)"],
             "data": [["1", "115/11/10", "新股甲", "9999", "上櫃", "115/11/05", "115/11/09", "50.0", "115/11/18", "1.2"],
                      ["2", "115/01/10", "舊股", "8888", "上市", "115/01/05", "115/01/09", "20", "115/01/18", "3"]]}
        r = ipo.collect(make_ctx({"publicForm": j}))
        self.assertEqual([x["code"] for x in r["items"]], ["9999"])

    def test_calendar_partial_failure(self):
        j = {"stat": "OK", "fields": ["資料日期", "股票代號", "股票名稱", "除權息前收盤價", "除權息參考價", "權值+息值", "權/息"],
             "data": [["115年11月10日", "2330", "台積電", "100", "94", "6", "息"]]}
        ctx = make_ctx({"TWT48U": j, "swagger": RuntimeError("down")})
        r = cal.collect(ctx)
        self.assertTrue(r["exdiv"][0]["high_yield"]); self.assertTrue(r["errors"])

    def test_notices_filter(self):
        major = [{"公司代號": "1111", "公司名稱": "甲", "主旨": "公告本公司召開董事會"},
                 {"公司代號": "2222", "公司名稱": "乙", "主旨": "公告本公司遭法院假扣押"},
                 {"公司代號": "2330", "公司名稱": "台積電", "主旨": "一般說明"}]
        routes = {"t187ap04_L": major, "t187ap04_O": [], "announcement/notice": [], "trading_warning": [],
                  "announcement/punish": [{"證券代號": "3333", "證券名稱": "丙", "處置原因": "連續漲停"}],
                  "disposal_information": [], "swagger": RuntimeError("x")}
        r = notices.collect(make_ctx(routes))
        codes = [x["code"] for x in r["items"]]
        self.assertNotIn("1111", codes); self.assertIn("2222", codes); self.assertIn("3333", codes)
        self.assertIn("2330", codes)  # 自選股保留

    def test_isolation_and_render(self):
        ctx = make_ctx({"finance/chart": yahoo([14] * 7)})
        results = {"vix": {"ok": True, "data": vix.collect(ctx)}, "rates": {"ok": False, "error": "boom"}}
        text = markdown.render(report_mod.build(ctx, results))
        self.assertIn("VIX", text); self.assertIn("boom", text)


if __name__ == "__main__":
    unittest.main()
