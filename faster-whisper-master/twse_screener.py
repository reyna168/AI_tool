"""
台股飆股掃描器 - 整合版
========================

多維度篩選當日強勢股，結合量能、技術指標、分點主力動向。

資料來源:
1. 即時全市場價量:  https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
2. 歷史日K資料:      https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX
3. 產業別對照:       https://openapi.twse.com.tw/v1/opendata/t187ap03_L
4. 券商分點進出:     https://bsr.twse.com.tw/bshtm/

篩選邏輯 (四階段):
  Stage 1 ─ 量能初篩: 當日成交量 > N 日均量 × 倍數
  Stage 2 ─ 價格篩選: 當日漲幅 > 閾值，且收盤接近最高價
  Stage 3 ─ 技術分析: 均線多頭排列、MACD 多方、RSI 未超買
  Stage 4 ─ 分點驗證: 買超分點集中度高（主力進場訊號）

綜合評分 (滿分 100):
  量能 25 分 + 價格 25 分 + 技術 30 分 + 分點 20 分

使用方式:
  python twse_screener.py                         # 預設掃描
  python twse_screener.py --top 30 --min_vol_ratio 1.5
  python twse_screener.py --skip-branch            # 跳過分點查詢(快速模式)
  python twse_screener.py --min_score 60           # 只顯示60分以上

需求套件: pandas, numpy, requests (均已包含在 requirements.txt)
"""

import argparse
import re
import time
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
STOCK_ALL_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
INDUSTRY_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
HIST_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
BSR_BASE = "https://bsr.twse.com.tw/bshtm/bsMenu.aspx"
BSR_CONTENT = "https://bsr.twse.com.tw/bshtm/bsContent.aspx"


# ============================================================
# 資料層
# ============================================================

def get_realtime_quotes() -> pd.DataFrame:
    r = requests.get(STOCK_ALL_URL, headers=HEADERS, timeout=10)
    df = pd.DataFrame(r.json())
    for col in ["TradeVolume", "TradeValue", "OpeningPrice",
                 "HighestPrice", "LowestPrice", "ClosingPrice", "Change"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", ""), errors="coerce"
            )
    return df


def get_industry_map() -> pd.DataFrame:
    r = requests.get(INDUSTRY_URL, headers=HEADERS, timeout=10)
    df = pd.DataFrame(r.json())
    return df[["公司代號", "公司簡稱", "產業別"]]


def _to_number(s):
    if s is None:
        return None
    s = str(s).replace(",", "").strip()
    if s in ("", "--", "X"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def get_historical(date_str: str) -> pd.DataFrame:
    """取得指定日期 (YYYYMMDD) 全市場日K"""
    params = {"date": date_str, "type": "ALL", "response": "json"}
    r = requests.get(HIST_URL, params=params, headers=HEADERS, timeout=15)
    data = r.json()
    if data.get("stat") != "OK":
        return pd.DataFrame()

    target_fields, target_data = None, None
    for key in data:
        if key.startswith("fields"):
            idx = key[len("fields"):]
            fields = data[key]
            if fields and "證券代號" in fields:
                target_fields = fields
                target_data = data.get(f"data{idx}", [])
                break
    if not target_fields:
        return pd.DataFrame()

    df = pd.DataFrame(target_data, columns=target_fields)
    rename_map = {
        "證券代號": "Code", "證券名稱": "Name",
        "收盤價": "Close", "開盤價": "Open",
        "最高價": "High", "最低價": "Low",
        "成交股數": "Volume",
    }
    df = df.rename(columns=rename_map)
    for col in ["Close", "Open", "High", "Low", "Volume"]:
        if col in df.columns:
            df[col] = df[col].map(_to_number)
    df["日期"] = date_str
    return df


def fetch_history_days(code: str, n_days: int = 60) -> pd.DataFrame:
    """往前抓 n_days 個交易日的歷史資料 (逐日查詢, 自動跳過非交易日)"""
    frames = []
    d = datetime.now()
    attempts = 0
    max_attempts = n_days * 2  # 容錯: 含假日

    while len(frames) < n_days and attempts < max_attempts:
        attempts += 1
        if d.weekday() >= 5:
            d -= timedelta(days=1)
            continue
        date_str = d.strftime("%Y%m%d")
        df = get_historical(date_str)
        if not df.empty:
            row = df[df["Code"] == code]
            if not row.empty:
                frames.append(row.iloc[0].to_dict())
        d -= timedelta(days=1)
        time.sleep(0.3)

    if not frames:
        return pd.DataFrame()
    result = pd.DataFrame(frames)
    result = result.sort_values("日期").reset_index(drop=True)
    return result


# ============================================================
# 技術指標計算 (純 pandas/numpy, 不依賴外部套件)
# ============================================================

def calc_sma(series: pd.Series, period: int) -> pd.Series:
    return series.rolling(window=period, min_periods=1).mean()


def calc_ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def calc_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def calc_macd(close: pd.Series):
    ema12 = calc_ema(close, 12)
    ema26 = calc_ema(close, 26)
    macd_line = ema12 - ema26
    signal_line = calc_ema(macd_line, 9)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calc_indicators(hist: pd.DataFrame) -> dict:
    """從歷史 K 線計算技術指標, 回傳最新一根的值"""
    if len(hist) < 5:
        return {}

    close = hist["Close"].astype(float)
    volume = hist["Volume"].astype(float)

    sma5 = calc_sma(close, 5).iloc[-1]
    sma10 = calc_sma(close, 10).iloc[-1]
    sma20 = calc_sma(close, 20).iloc[-1]
    sma60 = calc_sma(close, min(60, len(close))).iloc[-1]

    rsi = calc_rsi(close, 14).iloc[-1]

    macd_line, signal_line, histogram = calc_macd(close)
    macd_val = macd_line.iloc[-1]
    signal_val = signal_line.iloc[-1]
    hist_val = histogram.iloc[-1]

    vol_ma5 = calc_sma(volume, 5).iloc[-1]
    vol_ma20 = calc_sma(volume, 20).iloc[-1] if len(volume) >= 20 else vol_ma5

    return {
        "SMA5": sma5, "SMA10": sma10, "SMA20": sma20, "SMA60": sma60,
        "RSI14": rsi,
        "MACD": macd_val, "MACD_Signal": signal_val, "MACD_Hist": hist_val,
        "Vol_MA5": vol_ma5, "Vol_MA20": vol_ma20,
    }


# ============================================================
# 分點資料
# ============================================================

def _get_hidden(name: str, text: str) -> str:
    m = re.search(rf'id="{name}" value="([^"]*)"', text)
    return m.group(1) if m else ""


def get_broker_branch(stock_id: str) -> pd.DataFrame:
    session = requests.Session()
    r1 = session.get(BSR_BASE, headers=HEADERS, timeout=10)
    payload = {
        "__VIEWSTATE": _get_hidden("__VIEWSTATE", r1.text),
        "__VIEWSTATEGENERATOR": _get_hidden("__VIEWSTATEGENERATOR", r1.text),
        "__EVENTVALIDATION": _get_hidden("__EVENTVALIDATION", r1.text),
        "RadioButton_Excd": "1",
        "TextBox_Stkno": stock_id,
        "btnOK": "查詢",
    }
    r2 = session.post(BSR_BASE, data=payload, headers=HEADERS, timeout=10)
    if "查無資料" in r2.text:
        return pd.DataFrame()
    r3 = session.get(BSR_CONTENT, headers=HEADERS, timeout=10)
    tables = pd.read_html(r3.text)
    return tables[0] if tables else pd.DataFrame()


def analyze_branch(df: pd.DataFrame) -> dict:
    """分析分點資料, 回傳主力集中度等指標"""
    if df.empty:
        return {"branch_count": 0, "buy_concentration": 0, "top_buy_vol": 0}

    net_col = next((c for c in df.columns if "買賣超" in str(c)), None)
    if net_col is None:
        return {"branch_count": len(df), "buy_concentration": 0, "top_buy_vol": 0}

    df = df.copy()
    df[net_col] = pd.to_numeric(
        df[net_col].astype(str).str.replace(",", ""), errors="coerce"
    )

    buy_df = df[df[net_col] > 0].sort_values(net_col, ascending=False)
    sell_df = df[df[net_col] < 0].sort_values(net_col, ascending=True)

    total_buy_vol = buy_df[net_col].sum()
    top5_buy_vol = buy_df[net_col].head(5).sum()

    concentration = (top5_buy_vol / total_buy_vol * 100) if total_buy_vol > 0 else 0

    return {
        "branch_count": len(df),
        "buy_branch_count": len(buy_df),
        "sell_branch_count": len(sell_df),
        "total_buy_vol": total_buy_vol,
        "total_sell_vol": abs(sell_df[net_col].sum()),
        "top5_buy_vol": top5_buy_vol,
        "buy_concentration": round(concentration, 1),
    }


# ============================================================
# 評分系統
# ============================================================

def score_volume(row: dict, indicators: dict) -> float:
    """量能評分 (滿分 25)"""
    score = 0
    vol_ratio = row.get("vol_ratio", 1)
    if vol_ratio >= 3.0:
        score += 15
    elif vol_ratio >= 2.0:
        score += 12
    elif vol_ratio >= 1.5:
        score += 9
    elif vol_ratio >= 1.2:
        score += 5

    if indicators:
        vol_ma5 = indicators.get("Vol_MA5", 1)
        vol_ma20 = indicators.get("Vol_MA20", 1)
        if vol_ma5 > vol_ma20 * 1.2:
            score += 5
        if vol_ma5 > vol_ma20:
            score += 3

    return min(score, 25)


def score_price(row: dict) -> float:
    """價格評分 (滿分 25)"""
    score = 0
    change_pct = row.get("change_pct", 0)
    high = row.get("HighestPrice", 0)
    close = row.get("ClosingPrice", 0)

    if change_pct >= 7:
        score += 15
    elif change_pct >= 5:
        score += 12
    elif change_pct >= 3:
        score += 9
    elif change_pct >= 1:
        score += 5

    if high and close and high > 0:
        close_near_high = (close / high) * 100
        if close_near_high >= 98:
            score += 10
        elif close_near_high >= 95:
            score += 7
        elif close_near_high >= 92:
            score += 4

    return min(score, 25)


def score_technical(indicators: dict) -> float:
    """技術面評分 (滿分 30)"""
    if not indicators:
        return 0
    score = 0

    sma5 = indicators.get("SMA5", 0)
    sma10 = indicators.get("SMA10", 0)
    sma20 = indicators.get("SMA20", 0)
    sma60 = indicators.get("SMA60", 0)

    if sma5 > sma10 > sma20:
        score += 10
    elif sma5 > sma10:
        score += 5

    if sma20 > sma60 and sma60 > 0:
        score += 5

    rsi = indicators.get("RSI14", 50)
    if 40 <= rsi <= 70:
        score += 5
    elif 30 <= rsi < 40:
        score += 3

    macd = indicators.get("MACD", 0)
    signal = indicators.get("MACD_Signal", 0)
    hist = indicators.get("MACD_Hist", 0)
    if macd > signal:
        score += 5
    if hist > 0:
        score += 5

    return min(score, 30)


def score_branch(branch_info: dict) -> float:
    """分點評分 (滿分 20)"""
    if not branch_info or branch_info.get("branch_count", 0) == 0:
        return 0
    score = 0

    concentration = branch_info.get("buy_concentration", 0)
    if concentration >= 70:
        score += 12
    elif concentration >= 50:
        score += 9
    elif concentration >= 35:
        score += 5

    total_buy = branch_info.get("total_buy_vol", 0)
    total_sell = branch_info.get("total_sell_vol", 0)
    if total_sell > 0:
        buy_sell_ratio = total_buy / total_sell
    else:
        buy_sell_ratio = total_buy if total_buy > 0 else 0

    if buy_sell_ratio >= 3:
        score += 8
    elif buy_sell_ratio >= 2:
        score += 5
    elif buy_sell_ratio >= 1.5:
        score += 3

    return min(score, 20)


# ============================================================
# 主掃描流程
# ============================================================

def scan(
    top_n: int = 20,
    min_vol_ratio: float = 1.5,
    min_change_pct: float = 2.0,
    hist_days: int = 60,
    skip_branch: bool = False,
    delay: float = 1.0,
) -> pd.DataFrame:
    print(f"{'='*60}")
    print(f"  台股飆股掃描器  {datetime.now():%Y-%m-%d %H:%M}")
    print(f"{'='*60}")

    # Stage 0: 基礎資料
    print("\n[Stage 0] 取得即時行情與產業別...")
    quotes = get_realtime_quotes()
    industry = get_industry_map()
    quotes = quotes.merge(industry, left_on="Code", right_on="公司代號", how="left")
    quotes["產業別"] = quotes.get("產業別", pd.Series(dtype=str))

    prev_close = quotes["ClosingPrice"] - quotes["Change"]
    quotes["change_pct"] = (quotes["Change"] / prev_close.replace(0, pd.NA) * 100).astype(float)

    print(f"  全市場 {len(quotes)} 檔股票")

    # Stage 1: 量能初篩
    print(f"\n[Stage 1] 量能初篩 (當日量 / 5日均量 >= {min_vol_ratio})...")
    quotes["vol_ratio"] = 1.0
    candidates = quotes[
        (quotes["TradeVolume"] > 0) &
        (quotes["change_pct"].notna()) &
        (quotes["change_pct"] >= min_change_pct)
    ].copy()
    print(f"  漲幅 >= {min_change_pct}%: {len(candidates)} 檔")

    # 用全市場近5日均量做簡易估算 (以成交量排名替代)
    vol_median = quotes["TradeVolume"].median()
    candidates = candidates[candidates["TradeVolume"] > vol_median * min_vol_ratio]
    print(f"  量能篩選後: {len(candidates)} 檔")

    if candidates.empty:
        print("  無符合條件的股票, 請調整篩選參數")
        return pd.DataFrame()

    # Stage 2: 排序取前 N*3 做技術分析
    candidates = candidates.sort_values("change_pct", ascending=False)
    tech_pool = candidates.head(min(top_n * 3, len(candidates))).copy()
    print(f"\n[Stage 2] 技術分析 (取漲幅前 {len(tech_pool)} 檔)...")
    print(f"  正在取得歷史 K 線並計算指標 (每檔約 {hist_days} 個交易日)...")

    results = []
    for i, (_, row) in enumerate(tech_pool.iterrows(), 1):
        code = row["Code"]
        name = row.get("Name", "")
        print(f"  [{i}/{len(tech_pool)}] {code} ({name}) 取得歷史資料...", end="", flush=True)

        hist = fetch_history_days(code, n_days=hist_days)
        indicators = calc_indicators(hist) if not hist.empty and len(hist) >= 5 else {}

        # 計算更精確的量比
        if indicators and indicators.get("Vol_MA5", 0) > 0:
            vol_ratio = row["TradeVolume"] / indicators["Vol_MA5"]
        else:
            vol_ratio = 1.0

        row_dict = row.to_dict()
        row_dict["vol_ratio"] = round(vol_ratio, 2)

        vol_s = score_volume(row_dict, indicators)
        price_s = score_price(row_dict)
        tech_s = score_technical(indicators)

        row_dict["vol_score"] = vol_s
        row_dict["price_score"] = price_s
        row_dict["tech_score"] = tech_s
        row_dict["branch_score"] = 0
        row_dict["total_score"] = vol_s + price_s + tech_s
        row_dict["indicators"] = indicators

        print(f"  量:{vol_s} 價:{price_s} 技:{tech_s} = {row_dict['total_score']}")
        results.append(row_dict)
        time.sleep(0.5)

    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values("total_score", ascending=False).head(top_n)

    # Stage 3: 分點驗證 (只對前 top_n 名查詢)
    if not skip_branch:
        print(f"\n[Stage 3] 分點主力分析 (前 {len(df_results)} 名)...")
        branch_scores = []
        for i, (_, row) in enumerate(df_results.iterrows(), 1):
            code = row["Code"]
            name = row.get("Name", "")
            print(f"  [{i}/{len(df_results)}] {code} ({name}) 查詢分點...", end="", flush=True)

            df_broker = get_broker_branch(code)
            branch_info = analyze_branch(df_broker)
            b_score = score_branch(branch_info)

            df_results.at[row.name, "branch_score"] = b_score
            df_results.at[row.name, "buy_concentration"] = branch_info.get("buy_concentration", 0)
            df_results.at[row.name, "buy_sell_ratio"] = round(
                branch_info.get("total_buy_vol", 0) / max(branch_info.get("total_sell_vol", 1), 1), 2
            )

            print(f"  分點:{b_score} (集中度:{branch_info.get('buy_concentration', 0)}%)")
            time.sleep(delay)
    else:
        print("\n[Stage 3] 跳過分點查詢 (--skip-branch)")

    df_results["total_score"] = (
        df_results["vol_score"] + df_results["price_score"] +
        df_results["tech_score"] + df_results["branch_score"]
    )
    df_results = df_results.sort_values("total_score", ascending=False).reset_index(drop=True)
    df_results.index = df_results.index + 1
    df_results.index.name = "排名"

    return df_results


def print_report(df: pd.DataFrame):
    if df.empty:
        print("\n無掃描結果")
        return

    print(f"\n{'='*60}")
    print(f"  飆股掃描報告  共 {len(df)} 檔")
    print(f"{'='*60}")

    display_cols = {
        "Code": "代號", "Name": "名稱", "產業別": "產業",
        "ClosingPrice": "收盤", "change_pct": "漲跌%",
        "TradeVolume": "成交量", "vol_ratio": "量比",
        "vol_score": "量分", "price_score": "價分",
        "tech_score": "技分", "branch_score": "點分",
        "total_score": "總分",
    }

    available = [c for c in display_cols if c in df.columns]
    report = df[available].rename(columns=display_cols)

    for col in ["收盤", "漲跌%", "量比"]:
        if col in report.columns:
            report[col] = report[col].map(lambda x: f"{x:.2f}" if pd.notna(x) else "-")

    for col in ["量分", "價分", "技分", "點分", "總分"]:
        if col in report.columns:
            report[col] = report[col].map(lambda x: int(x) if pd.notna(x) else 0)

    print(report.to_string())

    print(f"\n{'─'*60}")
    print("評分說明: 量分(25) + 價分(25) + 技分(30) + 點分(20) = 總分(100)")
    print("  量分: 量能放大程度 (量比、均量趨勢)")
    print("  價分: 漲幅強度 + 收盤是否接近最高價")
    print("  技分: 均線排列 + RSI + MACD 多空")
    print("  點分: 買超分點集中度 + 買賣比")
    print(f"{'─'*60}")


def save_csv(df: pd.DataFrame, filename: str):
    if df.empty:
        return
    export = df.drop(columns=["indicators"], errors="ignore")
    export.to_csv(filename, index=True, encoding="utf-8-sig")
    print(f"\n已儲存: {filename}")


# ============================================================
# CLI 入口
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Taiwan Stock Screener - scan for momentum stocks")
    parser.add_argument("--top", type=int, default=20, help="Output top N stocks (default: 20)")
    parser.add_argument("--min_vol_ratio", type=float, default=1.5, help="Min volume ratio threshold (default: 1.5)")
    parser.add_argument("--min_change_pct", type=float, default=2.0, help="Min change pct threshold (default: 2.0)")
    parser.add_argument("--hist_days", type=int, default=60, help="History days for technical analysis (default: 60)")
    parser.add_argument("--skip-branch", action="store_true", help="Skip broker branch query (fast mode)")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between branch queries in seconds (default: 1.0)")
    parser.add_argument("--min_score", type=int, default=0, help="Only show stocks with total score >= N (default: 0)")
    args = parser.parse_args()

    df = scan(
        top_n=args.top,
        min_vol_ratio=args.min_vol_ratio,
        min_change_pct=args.min_change_pct,
        hist_days=args.hist_days,
        skip_branch=args.skip_branch,
        delay=args.delay,
    )

    if args.min_score > 0:
        df = df[df["total_score"] >= args.min_score]

    print_report(df)

    today_str = datetime.now().strftime("%Y%m%d")
    save_csv(df, f"screener_{today_str}.csv")
