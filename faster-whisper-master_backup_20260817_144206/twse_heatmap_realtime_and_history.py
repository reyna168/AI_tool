"""
台股「產業熱力圖」擷取工具 - 即時當日 + 歷史多日回顧

資料來源 (TWSE 官方, 免金鑰):
1. 即時（最近一個交易日）全部股票價量:
   https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL
2. 歷史指定日期全部股票價量:
   https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date=YYYYMMDD&type=ALL&response=json
3. 上市公司產業類別對照表:
   https://openapi.twse.com.tw/v1/opendata/t187ap03_L

功能:
- get_all_stock_quotes()             即時（最近交易日）全部股票價量
- get_historical_all_stocks(date)    指定日期全部股票價量 (可回溯查詢)
- build_merged_data()                即時股價 + 產業別
- build_historical_merged(dates)     多日資料合併，含「日期」欄位
- sector_heatmap_summary(df)         單日：各產業加權平均漲跌幅彙總
- sector_heatmap_matrix(df_hist)     多日：產業 x 日期 矩陣 (經典熱力圖用)
- get_hot_stocks / get_hot_stocks_by_sector   熱門股排行
- plot_treemap(df, path)             單日 Treemap 熱力圖
- plot_treemap_animated(df_hist, path)  多日動態 Treemap (拖拉日期播放)
- plot_sector_matrix_heatmap(df_hist, path)  多日 產業x日期 矩陣熱力圖

注意事項:
- MI_INDEX 是逐日查詢，抓多天要迴圈呼叫；程式已加入 time.sleep()，
  請勿移除，避免對證交所伺服器造成過大負擔或被暫時封鎖。
- 非交易日 (週末、國定假日) 該日 API 會回傳 stat != 'OK'，程式會自動跳過。
- 產業別對照表沒有歷史版本，此處假設近期分類不變，統一套用最新版本。
- 只涵蓋上市 (TWSE)，上櫃 (TPEx) 需另外串 TPEx OpenAPI。
- 因沙盒網路限制未能實際連線測試，請於本機環境先執行，並用
  print(df.columns) 確認欄位是否與程式假設一致（證交所偶爾會微調格式）。
"""

import time
from datetime import datetime, timedelta

import pandas as pd
import requests

HEADERS = {"User-Agent": "Mozilla/5.0"}


# ---------- 產業別對照表 ----------

def get_industry_classification() -> pd.DataFrame:
    url = "https://openapi.twse.com.tw/v1/opendata/t187ap03_L"
    r = requests.get(url, headers=HEADERS, timeout=10)
    df = pd.DataFrame(r.json())
    return df[["公司代號", "公司簡稱", "產業別"]]


# ---------- 即時 (最近交易日) ----------

def get_all_stock_quotes() -> pd.DataFrame:
    url = "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL"
    r = requests.get(url, headers=HEADERS, timeout=10)
    df = pd.DataFrame(r.json())
    numeric_cols = ["TradeVolume", "TradeValue", "OpeningPrice", "HighestPrice",
                     "LowestPrice", "ClosingPrice", "Change", "Transaction"]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ""), errors="coerce")
    return df


# ---------- 歷史 (指定日期) ----------

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


def get_historical_all_stocks(date: str) -> pd.DataFrame:
    """date 格式 YYYYMMDD。非交易日會回傳空 DataFrame。"""
    url = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
    params = {"date": date, "type": "ALL", "response": "json"}
    r = requests.get(url, params=params, headers=HEADERS, timeout=15)
    data = r.json()
    if data.get("stat") != "OK":
        print(f"{date}: 無資料 (非交易日或查詢失敗) - {data.get('stat')}")
        return pd.DataFrame()

    # 自動尋找「個股收盤行情」表格 (欄位含「證券代號」)，避免硬編索引
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
        print(f"{date}: 找不到個股收盤行情表格，證交所格式可能異動")
        return pd.DataFrame()

    df = pd.DataFrame(target_data, columns=target_fields)
    df["日期"] = date

    rename_map = {"證券代號": "Code", "證券名稱": "Name", "收盤價": "ClosingPrice",
                  "成交股數": "TradeVolume", "成交金額": "TradeValue",
                  "漲跌價差": "ChangeAbs", "漲跌(+/-)": "ChangeSign"}
    df = df.rename(columns=rename_map)

    for col in ["ClosingPrice", "TradeVolume", "TradeValue", "ChangeAbs"]:
        if col in df.columns:
            df[col] = df[col].map(_to_number)

    if "ChangeSign" in df.columns and "ChangeAbs" in df.columns:
        sign = df["ChangeSign"].astype(str).str.contains("-").map(lambda x: -1 if x else 1)
        df["Change"] = df["ChangeAbs"].fillna(0) * sign
    else:
        df["Change"] = 0

    return df


def generate_trade_dates(start: str, end: str):
    """產生 start~end (含) 區間內的日期字串 (YYYYMMDD)，排除週末；
    國定假日仍需靠 API 回傳 stat!=OK 自動跳過。"""
    d0 = datetime.strptime(start, "%Y%m%d")
    d1 = datetime.strptime(end, "%Y%m%d")
    d = d0
    dates = []
    while d <= d1:
        if d.weekday() < 5:
            dates.append(d.strftime("%Y%m%d"))
        d += timedelta(days=1)
    return dates


# ---------- 合併資料 ----------

def _compute_change_pct(df):
    prev_close = df["ClosingPrice"] - df["Change"]
    df["漲跌幅(%)"] = (df["Change"] / prev_close.replace(0, pd.NA) * 100).astype(float)
    return df


def build_merged_data() -> pd.DataFrame:
    """即時（最近交易日）股價 + 產業別"""
    quotes = get_all_stock_quotes()
    industry = get_industry_classification()
    df = quotes.merge(industry, left_on="Code", right_on="公司代號", how="inner")
    return _compute_change_pct(df)


def build_historical_merged(dates: list) -> pd.DataFrame:
    """多日歷史股價 + 產業別，dates 為 YYYYMMDD 字串列表"""
    industry = get_industry_classification()
    frames = []
    for d in dates:
        daily = get_historical_all_stocks(d)
        if daily.empty:
            continue
        merged = daily.merge(industry, left_on="Code", right_on="公司代號", how="inner")
        frames.append(_compute_change_pct(merged))
        time.sleep(1.5)  # 禮貌性延遲，避免對證交所伺服器造成過大負擔
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ---------- 彙總 / 排行 ----------

def sector_heatmap_summary(df: pd.DataFrame) -> pd.DataFrame:
    """單日：各產業加權平均漲跌幅彙總"""
    rows = []
    for sector, g in df.groupby("產業別"):
        w = g["TradeValue"]
        weighted_change = (g["漲跌幅(%)"] * w).sum() / w.sum() if w.sum() else g["漲跌幅(%)"].mean()
        rows.append({"產業別": sector, "加權平均漲跌幅(%)": round(weighted_change, 2),
                      "產業總成交值": int(w.sum()), "股票檔數": len(g)})
    return pd.DataFrame(rows).sort_values("加權平均漲跌幅(%)", ascending=False).reset_index(drop=True)


def sector_heatmap_matrix(df_hist: pd.DataFrame) -> pd.DataFrame:
    """多日：產業 x 日期 矩陣，值為當日成交值加權平均漲跌幅(%)"""
    def weighted(g):
        w = g["TradeValue"]
        return (g["漲跌幅(%)"] * w).sum() / w.sum() if w.sum() else g["漲跌幅(%)"].mean()

    summary = df_hist.groupby(["產業別", "日期"]).apply(weighted).reset_index(name="加權平均漲跌幅(%)")
    return summary.pivot(index="產業別", columns="日期", values="加權平均漲跌幅(%)")


def get_hot_stocks(df: pd.DataFrame, by: str = "成交值", top_n: int = 20) -> pd.DataFrame:
    col_map = {"成交值": "TradeValue", "成交量": "TradeVolume", "漲跌幅": "漲跌幅(%)"}
    sort_col = col_map.get(by, "TradeValue")
    return df.sort_values(sort_col, ascending=False)[
        ["Code", "Name", "產業別", "ClosingPrice", "漲跌幅(%)", "TradeVolume", "TradeValue"]
    ].head(top_n)


def get_hot_stocks_by_sector(df: pd.DataFrame, sector: str, top_n: int = 5) -> pd.DataFrame:
    sub = df[df["產業別"] == sector]
    return get_hot_stocks(sub, by="成交值", top_n=top_n)


# ---------- 視覺化 ----------

def plot_treemap(df: pd.DataFrame, output_path: str = "heatmap_today.html"):
    """單日 Treemap 熱力圖 (大小=成交值, 顏色=漲跌幅, 紅漲綠跌)"""
    import plotly.express as px
    fig = px.treemap(df, path=["產業別", "Name"], values="TradeValue", color="漲跌幅(%)",
                      color_continuous_scale="RdYlGn_r", color_continuous_midpoint=0,
                      title="台股類股熱力圖 - 即時 (紅漲綠跌)")
    fig.write_html(output_path)
    print(f"已輸出 {output_path}")


def plot_treemap_animated(df_hist: pd.DataFrame, output_path: str = "heatmap_history_animated.html"):
    """多日動態 Treemap，可用日期滑桿切換播放"""
    import plotly.express as px
    fig = px.treemap(df_hist, path=["產業別", "Name"], values="TradeValue", color="漲跌幅(%)",
                      color_continuous_scale="RdYlGn_r", color_continuous_midpoint=0,
                      animation_frame="日期", title="台股類股熱力圖 - 歷史回顧 (紅漲綠跌)")
    fig.write_html(output_path)
    print(f"已輸出 {output_path}")


def plot_sector_matrix_heatmap(df_hist: pd.DataFrame, output_path: str = "heatmap_sector_matrix.html"):
    """多日 產業 x 日期 矩陣熱力圖 (經典格狀 heatmap，適合看版塊持續強弱)"""
    import plotly.express as px
    matrix = sector_heatmap_matrix(df_hist)
    fig = px.imshow(matrix, color_continuous_scale="RdYlGn_r", color_continuous_midpoint=0,
                     aspect="auto", labels=dict(color="漲跌幅(%)"),
                     title="各產業近期漲跌幅矩陣 (紅漲綠跌)")
    fig.write_html(output_path)
    print(f"已輸出 {output_path}")


if __name__ == "__main__":
    # === 1. 即時當日熱力圖 ===
    print("抓取即時（最近交易日）資料...")
    df_today = build_merged_data()
    print(sector_heatmap_summary(df_today))
    print(get_hot_stocks(df_today, by="成交值", top_n=20))
    plot_treemap(df_today, "heatmap_today.html")

    # === 2. 歷史多日回顧 (範例: 依需求調整日期區間) ===
    print("\n抓取歷史多日資料...")
    dates = generate_trade_dates("20260706", "20260713")
    df_hist = build_historical_merged(dates)
    if not df_hist.empty:
        print(sector_heatmap_matrix(df_hist))
        plot_treemap_animated(df_hist, "heatmap_history_animated.html")
        plot_sector_matrix_heatmap(df_hist, "heatmap_sector_matrix.html")
