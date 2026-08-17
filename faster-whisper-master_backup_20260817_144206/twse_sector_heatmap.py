"""
台股「類股/產業」熱力圖 及 熱門股 擷取工具

資料來源 (皆為 TWSE 官方 OpenAPI, 免金鑰):
1. 最近一個交易日全部股票的價量資訊:
   https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
2. 上市公司產業類別對照表 (股票代號 -> 產業別):
   https://openapi.twse.com.tw/v1/opendata/t187ap03_L

流程:
1. 抓全部股票的收盤價、漲跌、成交量值
2. 抓公司產業別對照表, 合併到股票資料上
3. 依產業分組, 算出「成交值加權平均漲跌幅」、「產業總成交值」 -> 熱力圖用資料
4. 依成交值 / 漲跌幅排序, 找出全市場 或 各產業的熱門股
5. (選用) 用 plotly 畫出 Treemap 熱力圖: 大小=成交值, 顏色=漲跌幅

注意:
- STOCK_DAY_ALL 只回傳「最近一個交易日」資料, 沒有歷史查詢參數;
  要抓歷史資料需改用 https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX
  並帶 date=YYYYMMDD 參數逐日查詢。
- 上櫃(TPEx)股票不在這個 API 內, 若需要上櫃資料要另外串接
  TPEx OpenAPI (https://www.tpex.org.tw/openapi/)。
- 本腳本因沙盒網路限制未能直接連線測試, 請於本機環境先執行並用
  print(df.columns) / df.head() 確認欄位是否與下方程式碼一致
  (證交所偶爾會微調欄位名稱)。
"""

import requests
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_all_stock_quotes() -> pd.DataFrame:
    """取得最近一個交易日全部上市股票的價量資訊"""
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    r = requests.get(url, headers=HEADERS, timeout=10)
    df = pd.DataFrame(r.json())
    numeric_cols = [
        "TradeVolume", "TradeValue", "OpeningPrice", "HighestPrice",
        "LowestPrice", "ClosingPrice", "Change", "Transaction",
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace(",", ""), errors="coerce"
            )
    return df


def get_industry_classification() -> pd.DataFrame:
    """取得上市公司「產業別」對照表"""
    url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
    r = requests.get(url, headers=HEADERS, timeout=10)
    df = pd.DataFrame(r.json())
    return df[["公司代號", "公司簡稱", "產業別"]]


def build_merged_data() -> pd.DataFrame:
    """合併股價資料與產業別, 並計算漲跌幅(%)"""
    quotes = get_all_stock_quotes()
    industry = get_industry_classification()
    df = quotes.merge(industry, left_on="Code", right_on="公司代號", how="inner")
    prev_close = df["ClosingPrice"] - df["Change"]
    df["漲跌幅(%)"] = (df["Change"] / prev_close.replace(0, pd.NA) * 100).astype(float)
    return df


def sector_heatmap_summary(df: pd.DataFrame) -> pd.DataFrame:
    """依產業別彙總: 成交值加權平均漲跌幅、總成交值、股票檔數 (即熱力圖底層數據)"""
    rows = []
    for sector, g in df.groupby("產業別"):
        w = g["TradeValue"]
        weighted_change = (g["漲跌幅(%)"] * w).sum() / w.sum() if w.sum() else g["漲跌幅(%)"].mean()
        rows.append({
            "產業別": sector,
            "加權平均漲跌幅(%)": round(weighted_change, 2),
            "產業總成交值": int(w.sum()),
            "股票檔數": len(g),
        })
    return pd.DataFrame(rows).sort_values("加權平均漲跌幅(%)", ascending=False).reset_index(drop=True)


def get_hot_stocks(df: pd.DataFrame, by: str = "成交值", top_n: int = 20) -> pd.DataFrame:
    """全市場熱門股排行 (預設依成交值; 也可傳 by='漲跌幅' 或 by='成交量')"""
    col_map = {"成交值": "TradeValue", "成交量": "TradeVolume", "漲跌幅": "漲跌幅(%)"}
    sort_col = col_map.get(by, "TradeValue")
    return df.sort_values(sort_col, ascending=False)[
        ["Code", "Name", "產業別", "ClosingPrice", "漲跌幅(%)", "TradeVolume", "TradeValue"]
    ].head(top_n)


def get_hot_stocks_by_sector(df: pd.DataFrame, sector: str, top_n: int = 5) -> pd.DataFrame:
    """單一產業內的熱門股 (依成交值排序)"""
    sub = df[df["產業別"] == sector]
    return get_hot_stocks(sub, by="成交值", top_n=top_n)


def plot_treemap(df: pd.DataFrame, output_path: str = "heatmap.html"):
    """用 Plotly 畫出產業/個股熱力圖 (大小=成交值, 顏色=漲跌幅)
    需先 pip install plotly
    台股習慣「紅漲綠跌」, 故使用反轉色階 RdYlGn_r。
    """
    import plotly.express as px

    fig = px.treemap(
        df,
        path=["產業別", "Name"],
        values="TradeValue",
        color="漲跌幅(%)",
        color_continuous_scale="RdYlGn_r",
        color_continuous_midpoint=0,
        title="台股類股熱力圖 (大小=成交值, 顏色=漲跌幅, 紅漲綠跌)",
    )
    fig.write_html(output_path)
    print(f"熱力圖已輸出至 {output_path}")


if __name__ == "__main__":
    df = build_merged_data()

    print("=== 各產業表現 (熱力圖數據) ===")
    print(sector_heatmap_summary(df))

    print("\n=== 全市場熱門股 Top 20 (依成交值) ===")
    print(get_hot_stocks(df, by="成交值", top_n=20))

    print("\n=== 半導體業熱門股 Top 5 (範例) ===")
    print(get_hot_stocks_by_sector(df, sector="半導體業", top_n=5))

    # 輸出互動式熱力圖 (需先 pip install plotly)
    plot_treemap(df)
