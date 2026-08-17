"""
台股「當日高成交量股票 × 分點進出」自動抓取程式

資料來源:
1. 即時全市場股票價量 (TWSE OpenAPI):
   https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
2. 個股分點進出明細 (TWSE 即時查詢系統, 僅當日):
   https://bsr.twse.com.tw/bshtm/

功能:
- 自動篩選當日成交量/成交值前 N 名股票
- 逐一查詢這些股票的「券商分點進出」明細
- 彙整買超/賣超前 N 名分點
- 輸出 CSV 方便後續分析

使用方式:
  python twse_high_volume_branch.py [--top 20] [--broker_top 10] [--market 上市]

注意事項:
- 分點資料通常要等當日交易結束後才有資料, 太早查詢會顯示「查無資料」
- 這是模擬 ASP.NET 表單流程, 若證交所網站改版可能需調整
- 請勿短時間大量查詢, 程式已加入延遲機制
- 只涵蓋上市 (TWSE), 上櫃 (TPEx) 需另外處理
"""

import argparse
import re
import time
from datetime import datetime

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
BSR_BASE = "https://bsr.twse.com.tw/bshtm/bsMenu.aspx"
BSR_CONTENT = "https://bsr.twse.com.tw/bshtm/bsContent.aspx"
STOCK_ALL_URL = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"


def get_all_stock_quotes() -> pd.DataFrame:
    r = requests.get(STOCK_ALL_URL, headers=HEADERS, timeout=10)
    df = pd.DataFrame(r.json())
    for col in ["TradeVolume", "TradeValue", "ClosingPrice", "Change"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", ""), errors="coerce"
            )
    return df


def get_top_volume_stocks(top_n: int = 20) -> pd.DataFrame:
    df = get_all_stock_quotes()
    df = df.sort_values("TradeVolume", ascending=False).head(top_n).copy()
    df.insert(0, "排名", range(1, len(df) + 1))
    df.insert(1, "查詢日期", datetime.now().strftime("%Y-%m-%d"))
    return df


def _get_hidden(name: str, text: str) -> str:
    m = re.search(rf'id="{name}" value="([^"]*)"', text)
    return m.group(1) if m else ""


def get_broker_branch_trading(stock_id: str) -> pd.DataFrame:
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
    if not tables:
        return pd.DataFrame()

    df = tables[0]
    df.insert(0, "股票代號", stock_id)
    return df


def rank_branch_trading(df: pd.DataFrame, top_n: int = 10):
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    net_col = next((c for c in df.columns if "買賣超" in str(c)), None)
    if net_col is None:
        return pd.DataFrame(), pd.DataFrame()

    df = df.copy()
    df[net_col] = pd.to_numeric(
        df[net_col].astype(str).str.replace(",", ""), errors="coerce"
    )
    buy_top = df.sort_values(net_col, ascending=False).head(top_n)
    sell_top = df.sort_values(net_col, ascending=True).head(top_n)
    return buy_top, sell_top


def fetch_high_volume_branch_data(
    top_n: int = 20, broker_top: int = 10, delay_sec: float = 2.0
) -> pd.DataFrame:
    print(f"[{datetime.now():%H:%M:%S}] 抓取當日成交量前 {top_n} 名股票...")
    top_stocks = get_top_volume_stocks(top_n)
    print(top_stocks[["排名", "Code", "Name", "TradeVolume", "TradeValue", "ClosingPrice"]].to_string(index=False))

    all_broker = []
    for i, row in top_stocks.iterrows():
        code = row["Code"]
        name = row.get("Name", "")
        print(f"\n[{i+1}/{len(top_stocks)}] 查詢 {code} ({name}) 分點資料...")
        df_broker = get_broker_branch_trading(code)
        if df_broker.empty:
            print(f"  {code} 查無分點資料")
            continue

        buy_top, sell_top = rank_branch_trading(df_broker, top_n=broker_top)

        print(f"  買超前 {broker_top} 分點:")
        if not buy_top.empty:
            print(buy_top.to_string(index=False))
        print(f"  賣超前 {broker_top} 分點:")
        if not sell_top.empty:
            print(sell_top.to_string(index=False))

        all_broker.append(df_broker)
        time.sleep(delay_sec)

    if all_broker:
        return pd.concat(all_broker, ignore_index=True)
    return pd.DataFrame()


def save_csv(df: pd.DataFrame, filename: str):
    if df.empty:
        print(f"資料為空, 未儲存 {filename}")
        return
    df.to_csv(filename, index=False, encoding="utf-8-sig")
    print(f"已儲存: {filename}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="台股當日高成交量股票 × 分點進出自動抓取")
    parser.add_argument("--top", type=int, default=20, help="篩選成交量前 N 名股票 (預設 20)")
    parser.add_argument("--broker_top", type=int, default=10, help="每檔股票列出買超/賣超前 N 名分點 (預設 10)")
    parser.add_argument("--delay", type=float, default=2.0, help="查詢間隔秒數 (預設 2.0)")
    args = parser.parse_args()

    df_all = fetch_high_volume_branch_data(
        top_n=args.top, broker_top=args.broker_top, delay_sec=args.delay
    )

    today_str = datetime.now().strftime("%Y%m%d")
    save_csv(df_all, f"high_volume_branch_{today_str}.csv")
