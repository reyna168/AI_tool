"""
台股「個股分點(券商)進出」擷取程式

資料來源: TWSE 官方即時查詢系統
https://bsr.twse.com.tw/bshtm/bsMenu.aspx

功能:
- 查詢單檔或多檔股票「當日」各券商分點的買進/賣出股數、買賣超
- 自動列出買超、賣超前 N 名分點
- 存成 CSV，方便之後用 Excel 或其他程式分析

限制 (務必先看):
- 這個系統只提供「當日」資料，查不到歷史某一天的分點進出。
- 通常要等當日交易時段結束、證交所後台更新後才查得到，太早查詢會顯示查無資料。
- 上市股票用 RadioButton_Excd = "1"，上櫃股票用 "2"。
- 這是模擬 ASP.NET 表單流程(__VIEWSTATE 等隱藏欄位)，若證交所網站改版，
  解析邏輯可能需要跟著調整。
- 因沙盒網路限制未能實際連線測試，請在本機環境先用 1 檔股票測試成功，
  並用 print(df.columns) 確認欄位名稱，再擴大到多檔股票批次查詢。
- 請勿短時間內對同一個 IP 大量查詢，適度加上延遲，避免被證交所暫時封鎖。
"""

import re
import time
from datetime import datetime

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}
BASE_URL = "https://bsr.twse.com.tw/bshtm/bsMenu.aspx"
CONTENT_URL = "https://bsr.twse.com.tw/bshtm/bsContent.aspx"


def _get_hidden(name: str, text: str) -> str:
    m = re.search(rf'id="{name}" value="([^"]*)"', text)
    return m.group(1) if m else ""


def get_broker_branch_trading(stock_id: str, market: str = "上市") -> pd.DataFrame:
    """
    取得指定股票當日各券商分點進出明細。
    market: "上市" 或 "上櫃"
    """
    session = requests.Session()
    r1 = session.get(BASE_URL, headers=HEADERS, timeout=10)

    excd = "1" if market == "上市" else "2"
    payload = {
        "__VIEWSTATE": _get_hidden("__VIEWSTATE", r1.text),
        "__VIEWSTATEGENERATOR": _get_hidden("__VIEWSTATEGENERATOR", r1.text),
        "__EVENTVALIDATION": _get_hidden("__EVENTVALIDATION", r1.text),
        "RadioButton_Excd": excd,
        "TextBox_Stkno": stock_id,
        "btnOK": "查詢",
    }
    r2 = session.post(BASE_URL, data=payload, headers=HEADERS, timeout=10)

    if "查無資料" in r2.text:
        print(f"[{stock_id}] 查無分點資料 (可能非交易時段、代號錯誤，或當日尚未更新)")
        return pd.DataFrame()

    r3 = session.get(CONTENT_URL, headers=HEADERS, timeout=10)
    tables = pd.read_html(r3.text)
    if not tables:
        print(f"[{stock_id}] 找不到分點資料表格")
        return pd.DataFrame()

    df = tables[0]
    df.insert(0, "股票代號", stock_id)
    df.insert(1, "查詢日期", datetime.now().strftime("%Y-%m-%d"))
    return df


def rank_brokers(df: pd.DataFrame, top_n: int = 10):
    """
    從分點資料中，分別列出買超前 N 名、賣超前 N 名的券商分點。
    需依實際回傳欄位調整比對關鍵字 (常見為: 券商, 買進股數, 賣出股數, 買賣超)
    """
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    net_col = next((c for c in df.columns if "買賣超" in str(c)), None)
    if net_col is None:
        print("找不到「買賣超」欄位，請先 print(df.columns) 確認實際欄位名稱")
        return pd.DataFrame(), pd.DataFrame()

    df = df.copy()
    df[net_col] = pd.to_numeric(
        df[net_col].astype(str).str.replace(",", ""), errors="coerce"
    )

    buy_top = df.sort_values(net_col, ascending=False).head(top_n)
    sell_top = df.sort_values(net_col, ascending=True).head(top_n)
    return buy_top, sell_top


def fetch_multiple_stocks(stock_ids: list, market: str = "上市", delay_sec: float = 2.0) -> pd.DataFrame:
    """批次查詢多檔股票的分點資料，合併成一份 DataFrame"""
    frames = []
    for i, stock_id in enumerate(stock_ids, 1):
        print(f"[{i}/{len(stock_ids)}] 查詢 {stock_id} 分點資料...")
        df = get_broker_branch_trading(stock_id, market=market)
        if not df.empty:
            frames.append(df)
        if i < len(stock_ids):
            time.sleep(delay_sec)  # 禮貌性延遲，避免對證交所伺服器造成過大負擔
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def save_to_csv(df: pd.DataFrame, filename: str):
    if df.empty:
        print(f"資料是空的，未儲存 {filename}")
        return
    df.to_csv(filename, index=False, encoding="utf-8-sig")  # utf-8-sig 讓 Excel 開啟中文不亂碼
    print(f"已儲存: {filename}")


if __name__ == "__main__":
    # 在這裡放要查詢的股票代號 (可以只放一檔，也可以放多檔)
    stock_ids = ["2330", "2317", "2454"]

    df_all = fetch_multiple_stocks(stock_ids, market="上市")

    if not df_all.empty:
        today_str = datetime.now().strftime("%Y%m%d")
        save_to_csv(df_all, f"broker_branch_{today_str}.csv")

        # 針對每一檔股票，各自列出買超/賣超前 10 名分點
        for stock_id in stock_ids:
            sub = df_all[df_all["股票代號"] == stock_id]
            buy_top, sell_top = rank_brokers(sub, top_n=10)
            print(f"\n=== {stock_id} 買超前 10 分點 ===")
            print(buy_top)
            print(f"\n=== {stock_id} 賣超前 10 分點 ===")
            print(sell_top)
    else:
        print("未取得任何分點資料，請確認是否為交易日、股票代號是否正確，或稍後再試。")
