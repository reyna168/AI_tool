這是我準備好的 STEP 11 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# STEP 11: 融資融券與散戶動態 - 備用救援程式碼
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 官方 FinMind 金鑰 (已配置專屬金鑰以確保高頻獲取無誤)
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoic2NyYXRjaGluYWkwMUBnbWFpbC5jb20iLCJlbWFpbCI6InNjcmF0Y2hpbmFpMDFAZ21haWwuY29tIiwidG9rZW5fdmVyc2lvbiI6Mn0.9gGYifRhHQNfV8al5CUJ_fpYLeHYII7oRngzn59yGPA"

if 'df' not in globals() or df.empty:
    import yfinance as yf
    df = yf.download('2330.TW', period='3y', auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]

end_date = df.index.max()
start_date = end_date - pd.Timedelta(days=365)
str_start = start_date.strftime('%Y-%m-%d')
str_end = end_date.strftime('%Y-%m-%d')

url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockMarginPurchaseShortSale&data_id=2330&start_date={str_start}&end_date={str_end}&token={FINMIND_TOKEN}"

try:
    res = requests.get(url, timeout=10)
    data = res.json()
    if data.get('msg') == 'success' and len(data.get('data', [])) > 0:
        margin_df = pd.DataFrame(data['data'])
        margin_df['date'] = pd.to_datetime(margin_df['date'])
        margin_df.set_index('date', inplace=True)
        margin_df = margin_df[['MarginPurchaseTodayBalance', 'ShortSaleTodayBalance']]
        margin_df.columns = ['margin_balance', 'short_balance']
    else:
        raise ValueError("FinMind 無法取得有效資料，啟動模擬數據")
except Exception as e:
    print(f"⚠️ API 獲取失敗 ({e})，已啟用模擬融資融券數據以利學習流程繼續進行。")
    date_range = pd.date_range(start=start_date, end=end_date, freq='B')
    np.random.seed(42)
    sim_margin = np.random.randint(15000, 35000, size=len(date_range))
    sim_short = np.random.randint(500, 4000, size=len(date_range))
    margin_df = pd.DataFrame({'margin_balance': sim_margin, 'short_balance': sim_short}, index=date_range)

df = df.merge(margin_df, left_index=True, right_index=True, how='left')
df['margin_balance'] = df['margin_balance'].ffill().fillna(0)
df['short_balance'] = df['short_balance'].ffill().fillna(0)
df['margin_ratio'] = np.where(df['margin_balance'] > 0, (df['short_balance'] / df['margin_balance']) * 100, 0)

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.03, subplot_titles=('2330 收盤價與融資混亂/安定區', '融資與融券餘額 (張)', '券資比 (%)'))
fig.add_trace(go.Scatter(x=df.index, y=df['close'], name='收盤價', line=dict(color='#2563eb', width=1.5)), row=1, col=1)

p90 = df['margin_balance'].quantile(0.9)
p10 = df['margin_balance'].quantile(0.1)

fig.add_trace(go.Bar(x=df.index, y=df['margin_balance'], name='融資餘額', marker_color='#ef4444', opacity=0.7), row=2, col=1)
fig.add_trace(go.Bar(x=df.index, y=df['short_balance'], name='融券餘額', marker_color='#10b981', opacity=0.7), row=2, col=1)
fig.add_trace(go.Scatter(x=df.index, y=df['margin_ratio'], name='券資比 %', line=dict(color='#8b5cf6', width=1.5)), row=3, col=1)

fig.update_layout(height=800, template='plotly_white', showlegend=True, title_text="台積電 散戶融資融券與券資比觀測")
fig.show()
print("✅ STEP 11 散戶籌碼指標與視覺化建構完成！")
```
