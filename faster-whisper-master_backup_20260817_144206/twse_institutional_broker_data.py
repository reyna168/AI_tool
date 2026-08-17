"""
台股每日「三大法人買賣超」+「個股分點進出量」擷取工具

資料來源:
1. 三大法人買賣超 (官方 TWSE 網站 JSON 介面)
   https://www.twse.com.tw/rwd/zh/fund/T86
2. 個股分點進出 (TWSE 官方即時查詢系統, 僅提供「當日」資料)
   https://bsr.twse.com.tw/bshtm/

注意事項:
- bsr.twse.com.tw 是模擬 ASP.NET 表單流程 (__VIEWSTATE 等隱藏欄位),
  若證交所網站改版,解析邏輯需要跟著調整。
- 該系統通常只在「當日交易時段後~收盤後一段時間」才有資料,非交易日或
  太早查詢會回傳「查無資料」。
- 請自行加上 time.sleep() 做請求間隔,避免對證交所伺服器造成負擔。
- 本腳本因沙盒網路限制未能直接連線測試,請在你本機環境執行前先確認
  欄位名稱是否與實際回傳一致 (print(df.columns) 檢查)。
"""
import re
import time
from datetime import datetime

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_institutional_trading(date: str) -> pd.DataFrame:
    """取得指定日期「三大法人買賣超日報」(全市場)。date 格式: YYYYMMDD"""
    url = "https://www.twse.com.tw/rwd/zh/fund/T86"
    params = {"date": date, "selectType": "ALL", "response": "json"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=10)
    data = r.json()
    if data.get("stat") != "OK":
        print(f"{date} 無資料或非交易日: {data.get('stat')}")
        return pd.DataFrame()
    df = pd.DataFrame(data["data"], columns=data["fields"])
    for col in df.columns[2:]:
        df[col] = df[col].astype(str).str.replace(",", "").astype(float)
    return df


def _get_hidden(name: str, text: str) -> str:
    m = re.search(rf'id="{name}" value="([^"]*)"', text)
    return m.group(1) if m else ""


def get_broker_branch_trading(stock_id: str) -> pd.DataFrame:
    """取得指定股票「當日」券商分點進出明細。"""
    session = requests.Session()
    base = "https://bsr.twse.com.tw/bshtm/bsMenu.aspx"
    r1 = session.get(base, headers=HEADERS, timeout=10)

    payload = {
        "__VIEWSTATE": _get_hidden("__VIEWSTATE", r1.text),
        "__VIEWSTATEGENERATOR": _get_hidden("__VIEWSTATEGENERATOR", r1.text),
        "__EVENTVALIDATION": _get_hidden("__EVENTVALIDATION", r1.text),
        "RadioButton_Excd": "1",  # 1: 上市, 2: 上櫃
        "TextBox_Stkno": stock_id,
        "btnOK": "查詢",
    }
    r2 = session.post(base, data=payload, headers=HEADERS, timeout=10)
    if "查無資料" in r2.text:
        print(f"{stock_id} 查無分點資料 (可能非交易時段或代號錯誤)")
        return pd.DataFrame()

    r3 = session.get(
        "https://bsr.twse.com.tw/bshtm/bsContent.aspx", headers=HEADERS, timeout=10
    )
    tables = pd.read_html(r3.text)
    return tables[0] if tables else pd.DataFrame()


def rank_top_volume_brokers(stock_id: str, top_n: int = 10) -> pd.DataFrame:
    """排序出當日分點進出量(買賣超絕對值)最大的前 N 個券商分點。"""
    df = get_broker_branch_trading(stock_id)
    if df.empty:
        return df

    vol_col = next(
        (c for c in df.columns if "買賣超" in str(c) or "總股數" in str(c)), None
    )
    if vol_col:
        df["abs_vol"] = (
            df[vol_col].astype(str).str.replace(",", "").astype(float).abs()
        )
        df = df.sort_values("abs_vol", ascending=False).head(top_n)
    return df


if __name__ == "__main__":
    today = datetime.now().strftime("%Y%m%d")

    # 1. 全市場三大法人買賣超
    df_inst = get_institutional_trading(today)
    print(df_inst.head())

    time.sleep(1)

    # 2. 個股分點進出量排行 (以台積電 2330 為例, 可換成任何股票代號)
    df_broker = rank_top_volume_brokers("2330", top_n=10)
    print(df_broker)
