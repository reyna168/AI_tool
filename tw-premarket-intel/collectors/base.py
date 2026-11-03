"""Collector 共用：Context、Yahoo chart、TWSE/TPEx OpenAPI（含 swagger 自動探索）。"""
import datetime as dt
import logging
from dataclasses import dataclass, field
from urllib.parse import quote

log = logging.getLogger("collector")


@dataclass
class Ctx:
    cfg: dict
    db: object
    fetcher: object
    today: dt.date
    shared: dict = field(default_factory=dict)   # collector 之間傳遞資訊（如 CB 發行公司代號）


# ---------- Yahoo ----------
def yahoo_closes(ctx, symbol, rng="6mo"):
    """回傳 [(YYYY-MM-DD, close)]。先用 chart API（走節流/快取），失敗改用 yfinance。"""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{quote(symbol)}"
        j = ctx.fetcher.get_json(url, params={"range": rng, "interval": "1d"})
        res = j["chart"]["result"][0]
        out = []
        for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
            if c is not None:
                out.append((dt.datetime.fromtimestamp(t, dt.timezone.utc).date().isoformat(), float(c)))
        if out:
            return out
    except Exception as e:
        log.warning("Yahoo chart %s failed: %s; trying yfinance", symbol, e)
    import yfinance as yf  # 備援
    h = yf.Ticker(symbol).history(period=rng)
    return [(i.date().isoformat(), float(v)) for i, v in h["Close"].dropna().items()]


# ---------- OpenAPI ----------
ROOT = {"twse": "https://openapi.twse.com.tw", "tpex": "https://www.tpex.org.tw/openapi"}
SWAGGER = {"twse": "https://openapi.twse.com.tw/v1/swagger.json",
           "tpex": "https://www.tpex.org.tw/openapi/swagger.json"}


def _url(site, path):
    return ROOT[site] + (path if path.startswith("/v1") else "/v1" + path)


def list_paths(ctx, site):
    """回傳 [(path, 說明文字)]，來源為 swagger.json。"""
    sw = ctx.fetcher.get_json(SWAGGER[site])
    out = []
    for p, spec in sw.get("paths", {}).items():
        meta = spec.get("get", {}) if isinstance(spec, dict) else {}
        out.append((p, f"{meta.get('summary', '')} {meta.get('description', '')}".strip()))
    return out


def discover(ctx, site, keywords):
    kws = [keywords] if isinstance(keywords, str) else list(keywords)
    return [(p, s) for p, s in list_paths(ctx, site) if any(k in p or k in s for k in kws)]


def fetch_rows(ctx, site, path=None, keywords=None):
    """抓 OpenAPI 的 list[dict]。指定 path 失敗時，用 keywords 從 swagger 探索替代路徑。"""
    tried = []
    if path:
        try:
            return _as_rows(ctx.fetcher.get_json(_url(site, path)))
        except Exception as e:
            tried.append(f"{path}: {e}")
            log.warning("OpenAPI %s %s failed: %s", site, path, e)
    if keywords:
        for p, s in discover(ctx, site, keywords):
            if p == path:
                continue
            try:
                rows = _as_rows(ctx.fetcher.get_json(_url(site, p)))
                if rows:
                    log.info("OpenAPI discovered %s %s (%s)", site, p, s[:40])
                    return rows
            except Exception as e:
                tried.append(f"{p}: {e}")
    raise RuntimeError(f"OpenAPI {site} no usable endpoint; tried {tried or keywords}")


def _as_rows(j):
    if isinstance(j, list):
        return [r for r in j if isinstance(r, dict)]
    raise ValueError("unexpected OpenAPI payload")


def stock_prices(ctx):
    """{股票代號: 收盤價}（上市 + 上櫃），同一個 run 內只抓一次。"""
    if "stock_prices" in ctx.shared:
        return ctx.shared["stock_prices"]
    from core.util import pick, to_float
    prices = {}
    for site, path, kw in (("twse", "/exchangeReport/STOCK_DAY_ALL", ["每日收盤行情"]),
                           ("tpex", "/tpex_mainboard_daily_close_quotes", ["收盤行情"])):
        try:
            for r in fetch_rows(ctx, site, path, kw):
                code = pick(r, ["Code", "SecuritiesCompanyCode", "證券代號", "股票代號"])
                close = to_float(pick(r, ["ClosingPrice", "Close", "收盤價", "收盤"]))
                if code and close:
                    prices[str(code).strip()] = close
        except Exception as e:
            log.warning("stock prices %s failed: %s", site, e)
    ctx.shared["stock_prices"] = prices
    return prices
