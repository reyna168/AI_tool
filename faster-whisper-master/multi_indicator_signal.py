"""
多指標整合訊號系統 (股票版)
================================
把 RSI / MACD / 均線多空 / 市場結構(近似版) 整合成加權評分,
產生「做多 / 做空 / 觀望」訊號。

需求套件:
    pip install yfinance pandas pandas_ta

台股代號範例: "2330.TW" (台積電), "2317.TW" (鴻海)
美股代號範例: "AAPL", "TSLA"
"""

import pandas as pd
import pandas_ta as ta
import yfinance as yf


# ============================================================
# 一、資料層:抓取股價資料
# ============================================================
def fetch_data(symbol: str, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    抓取股價K線資料
    symbol: 股票代號 (台股需加 .TW, 例如 "2330.TW")
    period: 抓取區間, 如 "6mo", "1y", "2y"
    interval: K棒週期, 如 "1d"(日線), "1h"(小時), "1wk"(週線)
    """
    df = yf.download(symbol, period=period, interval=interval, progress=False)
    if df.empty:
        raise ValueError(f"抓不到資料,請確認股票代號是否正確: {symbol}")

    # yfinance 新版有時會回傳多層欄位, 這裡做扁平化處理
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    df = df.rename(columns={
        "Open": "open", "High": "high", "Low": "low",
        "Close": "close", "Volume": "volume"
    })
    return df


# ============================================================
# 二、指標運算層:每個指標各自輸出標準化訊號 (-1, 0, 1)
# ============================================================
def rsi_signal(df: pd.DataFrame, period: int = 14,
                overbought: float = 70, oversold: float = 30) -> int:
    """RSI 超買超賣訊號"""
    rsi = ta.rsi(df["close"], length=period)
    latest = rsi.iloc[-1]
    if pd.isna(latest):
        return 0
    if latest < oversold:
        return 1
    elif latest > overbought:
        return -1
    return 0


def macd_signal(df: pd.DataFrame) -> int:
    """MACD 金叉死叉訊號"""
    macd_df = ta.macd(df["close"])
    macd_line = macd_df["MACD_12_26_9"].iloc[-1]
    signal_line = macd_df["MACDs_12_26_9"].iloc[-1]
    if pd.isna(macd_line) or pd.isna(signal_line):
        return 0
    return 1 if macd_line > signal_line else -1


def ma_signal(df: pd.DataFrame, short: int = 20, long: int = 60) -> int:
    """均線多空排列訊號"""
    ma_short = ta.sma(df["close"], length=short).iloc[-1]
    ma_long = ta.sma(df["close"], length=long).iloc[-1]
    if pd.isna(ma_short) or pd.isna(ma_long):
        return 0
    return 1 if ma_short > ma_long else -1


def market_structure_signal(df: pd.DataFrame, lookback: int = 20) -> int:
    """
    市場結構近似判斷 (簡化版, 非原版付費指標邏輯)
    邏輯: 收盤價是否突破前 N 根K棒的高點/低點,
    近似「結構突破 (Break of Structure)」的概念。

    注意: 若要還原特定付費指標(如KNN市場結構框架)的精確邏輯,
    需要該指標公開原始碼, 否則此函式僅為近似替代方案。
    """
    struct_high = df["high"].rolling(lookback).max().shift(1).iloc[-1]
    struct_low = df["low"].rolling(lookback).min().shift(1).iloc[-1]
    close = df["close"].iloc[-1]

    if pd.isna(struct_high) or pd.isna(struct_low):
        return 0
    if close > struct_high:
        return 1
    elif close < struct_low:
        return -1
    return 0


# ============================================================
# 三、訊號整合層:加權投票
# ============================================================
def combine_signals(df: pd.DataFrame, weights: dict = None) -> dict:
    """
    整合所有指標訊號並回傳評分結果
    weights: 各指標權重, 預設可自行調整
    """
    if weights is None:
        weights = {
            "rsi": 1.0,
            "macd": 1.5,
            "ma": 1.0,
            "structure": 2.0,
        }

    raw_signals = {
        "rsi": rsi_signal(df),
        "macd": macd_signal(df),
        "ma": ma_signal(df),
        "structure": market_structure_signal(df),
    }

    weighted_score = sum(raw_signals[k] * weights[k] for k in raw_signals)
    max_possible = sum(weights.values())

    if weighted_score >= max_possible * 0.6:
        decision = "強力做多"
    elif weighted_score >= max_possible * 0.25:
        decision = "偏多"
    elif weighted_score <= -max_possible * 0.6:
        decision = "強力做空"
    elif weighted_score <= -max_possible * 0.25:
        decision = "偏空"
    else:
        decision = "觀望"

    return {
        "raw_signals": raw_signals,
        "weighted_score": round(weighted_score, 2),
        "max_possible_score": max_possible,
        "decision": decision,
    }


# ============================================================
# 四、風控層:簡易倉位計算 (依風險金額反推股數)
# ============================================================
def position_sizing(account_balance: float, entry_price: float,
                     stop_loss_price: float, risk_pct: float = 0.01) -> int:
    """
    account_balance: 帳戶總資金
    entry_price: 預計進場價
    stop_loss_price: 停損價
    risk_pct: 單筆願意承擔的風險比例 (預設1%)
    回傳: 建議買進股數(向下取整至整股)
    """
    risk_amount = account_balance * risk_pct
    risk_per_share = abs(entry_price - stop_loss_price)
    if risk_per_share == 0:
        return 0
    shares = int(risk_amount / risk_per_share)
    return shares


# ============================================================
# 五、主程式:單一股票分析範例
# ============================================================
def analyze_stock(symbol: str, period: str = "1y", interval: str = "1d"):
    print(f"\n=== 分析標的: {symbol} ===")
    df = fetch_data(symbol, period=period, interval=interval)

    result = combine_signals(df)

    print(f"最新收盤價: {df['close'].iloc[-1]:.2f}")
    print("各指標原始訊號 (1=多, -1=空, 0=中性):")
    for name, val in result["raw_signals"].items():
        print(f"  - {name}: {val}")
    print(f"加權總分: {result['weighted_score']} / 最高可能分: {result['max_possible_score']}")
    print(f"綜合判斷: {result['decision']}")

    return result


if __name__ == "__main__":
    # ---- 範例1: 台股單一標的分析 ----
    analyze_stock("2330.TW", period="1y", interval="1d")

    # ---- 範例2: 批次掃描多檔股票 ----
    watchlist = ["2330.TW", "2317.TW", "2454.TW"]
    print("\n\n=== 批次掃描結果 ===")
    for stock in watchlist:
        try:
            r = analyze_stock(stock)
        except ValueError as e:
            print(e)

    # ---- 範例3: 風控倉位計算 ----
    shares = position_sizing(
        account_balance=1_000_000,
        entry_price=600,
        stop_loss_price=580,
        risk_pct=0.01,
    )
    print(f"\n建議買進股數 (風險1%): {shares} 股")
