這是我準備好的 STEP 18 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# STEP 18: 純粹 Pandas 向量化回測 - 備用救援程式碼
import pandas as pd
import numpy as np
import plotly.graph_objects as go

if 'X_test_mega' not in globals() or 'y_pred_mega' not in globals():
    raise ValueError("請先執行 STEP 17 產出 X_test_mega 與 y_pred_mega！")

backtest_df = pd.DataFrame(index=X_test_mega.index)
backtest_df['Daily_Return'] = mega_df_cleaned_final.loc[X_test_mega.index, 'Daily_Return_1d']
backtest_df['Signal'] = y_pred_mega

# 計算持有報酬 (今日訊號 -> 明日持有)
backtest_df['Position'] = backtest_df['Signal'].shift(1).fillna(0)
backtest_df['Strategy_Return'] = backtest_df['Position'] * backtest_df['Daily_Return']

# 加入摩擦成本 (0.3%)
backtest_df['Trade_Action'] = backtest_df['Signal'].diff().abs().fillna(0)
backtest_df['Friction_Cost'] = backtest_df['Trade_Action'] * 0.3
backtest_df['Net_Strategy_Return'] = backtest_df['Strategy_Return'] - backtest_df['Friction_Cost']

# 計算累積淨值
backtest_df['Buy_Hold_Equity'] = (1 + backtest_df['Daily_Return'] / 100).cumprod()
backtest_df['AI_Strategy_Equity'] = (1 + backtest_df['Net_Strategy_Return'] / 100).cumprod()

fig = go.Figure()
fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Buy_Hold_Equity'], mode='lines', name='買進持有 (Buy & Hold)', line=dict(color='#94a3b8', dash='dash')))
fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['AI_Strategy_Equity'], mode='lines', name='AI 量化策略 (含交易成本)', line=dict(color='#2563eb', width=2)))

fig.update_layout(title='向量化回測：AI 策略 vs 買進持有 淨值曲線', yaxis_title='累積淨值 (Multiplier)', template='plotly_white', height=500)
fig.show()

total_bh_return = (backtest_df['Buy_Hold_Equity'].iloc[-1] - 1) * 100
total_ai_return = (backtest_df['AI_Strategy_Equity'].iloc[-1] - 1) * 100
print(f"📈 買進持有總報酬率: {total_bh_return:.2f}%")
print(f"🤖 AI 量化策略總報酬率: {total_ai_return:.2f}%")
```
