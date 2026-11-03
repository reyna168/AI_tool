這是我準備好的 STEP 14 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# STEP 14: 進階領先籌碼 (期貨與借券) - 備用救援程式碼
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 官方 FinMind 金鑰
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoic2NyYXRjaGluYWkwMUBnbWFpbC5jb20iLCJlbWFpbCI6InNjcmF0Y2hpbmFpMDFAZ21haWwuY29tIiwidG9rZW5fdmVyc2lvbiI6Mn0.9gGYifRhHQNfV8al5CUJ_fpYLeHYII7oRngzn59yGPA"

end_date = df.index.max()
start_date = end_date - pd.Timedelta(days=365)
str_start = start_date.strftime('%Y-%m-%d')
str_end = end_date.strftime('%Y-%m-%d')

# 獲取台指期法人數據
try:
    url_tx = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanFuturesInstitutionalInvestors&data_id=TX&start_date={str_start}&end_date={str_end}&token={FINMIND_TOKEN}"
    res_tx = requests.get(url_tx, timeout=10).json()
    if res_tx.get('msg') == 'success' and len(res_tx.get('data', [])) > 0:
        tx_df = pd.DataFrame(res_tx['data'])
        tx_df = tx_df[tx_df['institutional_investors'] == '外資']
        tx_df['date'] = pd.to_datetime(tx_df['date'])
        tx_df.set_index('date', inplace=True)
        tx_df['Foreign_TX_Net_OI'] = tx_df['long'] - tx_df['short']
        tx_series = tx_df['Foreign_TX_Net_OI']
    else:
        raise ValueError("無法取得期貨數據")
except Exception as e:
    print(f"⚠️ 期貨 API 獲取失敗 ({e})，使用模擬數據。")
    date_rng = pd.date_range(start_date, end_date, freq='B')
    np.random.seed(14)
    tx_series = pd.Series(np.random.randint(-20000, 20000, len(date_rng)), index=date_rng, name='Foreign_TX_Net_OI')

# 獲取借券賣出餘額
try:
    url_lend = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockSecuritiesLending&data_id=2330&start_date={str_start}&end_date={str_end}&token={FINMIND_TOKEN}"
    res_lend = requests.get(url_lend, timeout=10).json()
    if res_lend.get('msg') == 'success' and len(res_lend.get('data', [])) > 0:
        lend_df = pd.DataFrame(res_lend['data'])
        lend_df['date'] = pd.to_datetime(lend_df['date'])
        lend_grp = lend_df.groupby('date')['volume'].sum()
        lend_grp.name = 'sell_balance'
    else:
        raise ValueError("無法取得借券數據")
except Exception as e:
    print(f"⚠️ 借券 API 獲取失敗 ({e})，使用模擬數據。")
    date_rng = pd.date_range(start_date, end_date, freq='B')
    np.random.seed(28)
    lend_grp = pd.Series(np.random.randint(5000, 60000, len(date_rng)), index=date_rng, name='sell_balance')

df_extended = df.copy()
df_extended = df_extended.merge(tx_series, left_index=True, right_index=True, how='left')
df_extended = df_extended.merge(lend_grp, left_index=True, right_index=True, how='left')
df_extended['Foreign_TX_Net_OI'] = df_extended['Foreign_TX_Net_OI'].ffill().fillna(0)
df_extended['sell_balance'] = df_extended['sell_balance'].ffill().fillna(0)

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.04, subplot_titles=('2330 收盤價', '外資台指期淨未平倉口數 (Foreign_TX_Net_OI)', '借券賣出餘額 (sell_balance)'))
fig.add_trace(go.Scatter(x=df_extended.index, y=df_extended['close'], name='收盤價', line=dict(color='#2563eb')), row=1, col=1)

colors = ['#10b981' if val >= 0 else '#ef4444' for val in df_extended['Foreign_TX_Net_OI']]
fig.add_trace(go.Bar(x=df_extended.index, y=df_extended['Foreign_TX_Net_OI'], marker_color=colors, name='外資期貨淨未平倉'), row=2, col=1)
fig.add_trace(go.Scatter(x=df_extended.index, y=df_extended['sell_balance'], fill='tozeroy', line=dict(color='#f59e0b'), name='借券賣出餘額'), row=3, col=1)

fig.update_layout(height=800, template='plotly_white', title_text="領先指標：外資期貨與借券佈局")
fig.show()
print("💡 【觀念輸出】：當外資期貨淨空單增加，且借券賣出攀升時，通常是法人正在避險佈局的先行訊號！")
```
