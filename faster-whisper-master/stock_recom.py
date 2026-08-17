import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# ============================
# 1. 定義台股類股成分股清單
# ============================

sector_stocks = {
    "IC_Design": [
        "2454.TW", "3034.TW", "3041.TW", "3481.TW", "3529.TW",
        "3545.TW", "3551.TW", "3579.TW", "5274.TW", "6533.TW"
    ],
    "Passive_Components": [
        "2327.TW", "2338.TW", "2492.TW", "3026.TW", "3379.TW",
        "3556.TW", "6832.TW"
    ],
    "Semiconductor_Materials": [
        "3437.TW", "3532.TW", "6488.TW", "6526.TW"
    ],
    "Power_Components": [
        "2343.TW", "2427.TW", "3013.TW", "3376.TW"
    ],
    "AI_Server_Supply": [
        "2357.TW", "2382.TW", "2324.TW", "2376.TW", "3231.TW"
    ]
}

# ============================
# 2. 真實數據抓取函數
# ============================

def get_stock_data_yfinance(stock_id, days=250):
    """使用 yfinance 抓取台股歷史股價"""
    try:
        ticker = yf.Ticker(stock_id)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        df = ticker.history(start=start_date, end=end_date)
        return df
    except Exception as e:
        print(f"Error fetching {stock_id}: {e}")
        return pd.DataFrame()

# ============================
# 3. 技術指標計算函數
# ============================

def calculate_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    exp1 = prices.ewm(span=fast, adjust=False).mean()
    exp2 = prices.ewm(span=slow, adjust=False).mean()
    macd = exp1 - exp2
    signal_line = macd.ewm(span=signal, adjust=False).mean()
    histogram = macd - signal_line
    return macd, signal_line, histogram

def calculate_ma(prices, window):
    return prices.rolling(window=window).mean()

# ============================
# 4. 個股分析函數
# ============================

def analyze_stock(stock_id, data_func=get_stock_data_yfinance):
    df = data_func(stock_id, days=250)
    
    if df.empty or len(df) < 120:
        return None
    
    close = df['Close']
    volume = df['Volume']
    
    ma20 = calculate_ma(close, 20).iloc[-1]
    ma60 = calculate_ma(close, 60).iloc[-1]
    ma120 = calculate_ma(close, 120).iloc[-1]
    current_price = close.iloc[-1]
    
    rsi = calculate_rsi(close, 14).iloc[-1]
    macd, signal, hist = calculate_macd(close)
    macd_value = macd.iloc[-1]
    macd_20d_ago = macd.iloc[-21]
    
    avg_volume = volume.rolling(window=20).mean().iloc[-1]
    current_volume = volume.iloc[-1]
    
    bullish_ma = (current_price > ma20 > ma60 > ma120)
    rsi_strong = rsi > 50
    macd_positive = macd_value > 0
    macd_improving = macd_value > macd_20d_ago
    volume_strong = current_volume > avg_volume
    
    score = sum([bullish_ma, rsi_strong, macd_positive, macd_improving, volume_strong])
    
    premium_ma20 = (current_price - ma20) / ma20 * 100 if ma20 > 0 else 0
    premium_ma60 = (current_price - ma60) / ma60 * 100 if ma60 > 0 else 0
    
    return {
        "stock_id": stock_id,
        "price": round(current_price, 2),
        "ma20": round(ma20, 2),
        "ma60": round(ma60, 2),
        "ma120": round(ma120, 2),
        "rsi": round(rsi, 2),
        "macd": round(macd_value, 4),
        "macd_20d_ago": round(macd_20d_ago, 4),
        "volume_ratio": round(current_volume / avg_volume, 2) if avg_volume > 0 else 0,
        "premium_ma20": round(premium_ma20, 2),
        "premium_ma60": round(premium_ma60, 2),
        "bullish_ma": bullish_ma,
        "rsi_strong": rsi_strong,
        "macd_positive": macd_positive,
        "macd_improving": macd_improving,
        "volume_strong": volume_strong,
        "score": score
    }

def analyze_sector(sector_name, stock_list, data_func=get_stock_data_yfinance):
    sector_results = []
    
    for stock_id in stock_list:
        result = analyze_stock(stock_id, data_func)
        if result:
            sector_results.append(result)
    
    if not sector_results:
        return None, []
    
    sector_avg_score = np.mean([r['score'] for r in sector_results])
    sector_avg_rsi = np.mean([r['rsi'] for r in sector_results])
    sector_avg_macd = np.mean([r['macd'] for r in sector_results])
    sector_bullish_pct = sum([1 for r in sector_results if r['bullish_ma']]) / len(sector_results) * 100
    sector_strong_stocks = sum([1 for r in sector_results if r['score'] >= 4])
    
    sector_summary = {
        "sector_name": sector_name,
        "total_stocks": len(stock_list),
        "analyzed_stocks": len(sector_results),
        "avg_score": round(sector_avg_score, 2),
        "avg_rsi": round(sector_avg_rsi, 2),
        "avg_macd": round(sector_avg_macd, 4),
        "bullish_ma_pct": round(sector_bullish_pct, 2),
        "strong_stocks_count": sector_strong_stocks
    }
    
    return sector_summary, sector_results

# ============================
# 5. 執行分析
# ============================

print("=" * 70)
print("台股類股轉強篩選器 - 分析報告")
print("=" * 70)
print(f"分析時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"數據來源：yfinance (真實數據)")
print("=" * 70)

all_sector_summaries = []
all_stock_results = []

for sector_name, stock_list in sector_stocks.items():
    print(f"\n分析類股：{sector_name}...")
    summary, results = analyze_sector(sector_name, stock_list)
    if summary:
        all_sector_summaries.append(summary)
        all_stock_results.extend(results)

# 類股排名
sector_df = pd.DataFrame(all_sector_summaries)
sector_df_sorted = sector_df.sort_values(by="avg_score", ascending=False).reset_index(drop=True)

print("\n【類股轉強排名】")
print("=" * 70)
for idx, row in sector_df_sorted.iterrows():
    print(f"{idx+1}. {row['sector_name']:25} | "
          f"評分：{row['avg_score']}/5 | "
          f"平均 RSI: {row['avg_rsi']:5.1f} | "
          f"多頭排列：{row['bullish_ma_pct']:5.1f}% | "
          f"強勢股：{row['strong_stocks_count']}檔")

# 輸出 CSV
sector_df_sorted.to_csv("sector_summary.csv", index=False, encoding="utf-8-sig")
stock_df = pd.DataFrame(all_stock_results)
stock_df_sorted = stock_df.sort_values(by="score", ascending=False).reset_index(drop=True)
stock_df_sorted.to_csv("stock_details.csv", index=False, encoding="utf-8-sig")

print(f"\n✓ 類股摘要已儲存至：sector_summary.csv")
print(f"✓ 個股詳細資料已儲存至：stock_details.csv")

# 篩選強勢股
print("\n【★ 最值得布局的類股（評分 >= 3.5）】")
print("=" * 70)
top_sectors = sector_df_sorted[sector_df_sorted["avg_score"] >= 3.5]
if not top_sectors.empty:
    for idx, row in top_sectors.iterrows():
        print(f"✓ {row['sector_name']:25} | 評分：{row['avg_score']}/5 | 強勢股：{row['strong_stocks_count']}檔")
else:
    print("目前無類股符合條件")

print("\n【★ 最值得布局的個股（評分 = 5）】")
print("=" * 70)
top_stocks = stock_df_sorted[stock_df_sorted["score"] == 5]
if not top_stocks.empty:
    for idx, row in top_stocks.iterrows():
        print(f"✓ {row['stock_id']:10} | 股價：{row['price']:7.2f} | RSI: {row['rsi']:5.1f} | MACD: {row['macd']:8.4f}")
else:
    print("目前無個股符合全部條件")

print("\n分析完成！")