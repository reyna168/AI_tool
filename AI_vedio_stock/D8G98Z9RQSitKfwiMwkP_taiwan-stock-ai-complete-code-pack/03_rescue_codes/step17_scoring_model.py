這是我準備好的 STEP 17 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# STEP 17: 建構 20+ 複合特徵矩陣 - 備用救援程式碼
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import plotly.express as px

mega_df = df.copy()

# 1. 動能特徵
mega_df['Daily_Return_1d'] = mega_df['close'].pct_change(1) * 100
mega_df['Daily_Return_3d'] = mega_df['close'].pct_change(3) * 100
mega_df['Daily_Return_5d'] = mega_df['close'].pct_change(5) * 100

ema12 = mega_df['close'].ewm(span=12, adjust=False).mean()
ema26 = mega_df['close'].ewm(span=26, adjust=False).mean()
dif = ema12 - ema26
dem = dif.ewm(span=9, adjust=False).mean()
mega_df['MACD_Hist'] = dif - dem

# 2. 波動與型態
ma20 = mega_df['close'].rolling(20).mean()
std20 = mega_df['close'].rolling(20).std()
upper_bb = ma20 + (2 * std20)
lower_bb = ma20 - (2 * std20)
mega_df['BB_Width'] = ((upper_bb - lower_bb) / ma20) * 100

tr1 = mega_df['high'] - mega_df['low']
tr2 = (mega_df['high'] - mega_df['close'].shift(1)).abs()
tr3 = (mega_df['low'] - mega_df['close'].shift(1)).abs()
tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
mega_df['Normalized_ATR'] = (tr.rolling(14).mean() / mega_df['close']) * 100

# 3. 跨市場特徵 (加入防呆)
try:
    market_data = yf.download(['^SOX', '^TNX', '^VIX'], period='3y', progress=False)['Close']
    if isinstance(market_data.columns, pd.MultiIndex):
        market_data.columns = [c[0].upper() for c in market_data.columns]
    mega_df['SOX_Return'] = market_data['^SOX'].pct_change() * 100
    mega_df['TNX_Change'] = market_data['^TNX'].pct_change() * 100
    mega_df['VIX_Change'] = market_data['^VIX'].pct_change() * 100
except Exception as e:
    print(f"⚠️ 跨市場數據下載受限 ({e})，使用模擬特徵。")
    mega_df['SOX_Return'] = np.random.randn(len(mega_df)) * 1.5
    mega_df['TNX_Change'] = np.random.randn(len(mega_df)) * 0.8
    mega_df['VIX_Change'] = np.random.randn(len(mega_df)) * 3.0

# 4. Lead-Lag 領先特徵
if 'Foreign_TX_Net_OI' not in mega_df.columns:
    mega_df['Foreign_TX_Net_OI'] = np.random.randint(-15000, 15000, len(mega_df))
if 'sell_balance' not in mega_df.columns:
    mega_df['sell_balance'] = np.random.randint(1000, 50000, len(mega_df))

mega_df['TX_Net_OI_Lag5'] = mega_df['Foreign_TX_Net_OI'].shift(5)
mega_df['Sell_Balance_Lag5'] = mega_df['sell_balance'].shift(5)

# 5. 標籤與清理
mega_df['Next_Close'] = mega_df['close'].shift(-1)
mega_df['Target'] = (mega_df['Next_Close'] > mega_df['close']).astype(int)

mega_df_cleaned_final = mega_df.dropna()
feature_cols_mega = [
    'Daily_Return_1d', 'Daily_Return_3d', 'Daily_Return_5d', 'MACD_Hist',
    'BB_Width', 'Normalized_ATR', 'SOX_Return', 'TNX_Change', 'VIX_Change',
    'Foreign_TX_Net_OI', 'sell_balance', 'TX_Net_OI_Lag5', 'Sell_Balance_Lag5'
]

X_mega = mega_df_cleaned_final[feature_cols_mega]
y_mega = mega_df_cleaned_final['Target']

X_train_mega, X_test_mega, y_train_mega, y_test_mega = train_test_split(X_mega, y_mega, test_size=0.2, shuffle=False)

rf_mega = RandomForestClassifier(n_estimators=200, random_state=42)
rf_mega.fit(X_train_mega, y_train_mega)
y_pred_mega = rf_mega.predict(X_test_mega)
acc_mega = accuracy_score(y_test_mega, y_pred_mega)

feat_importances = pd.Series(rf_mega.feature_importances_, index=feature_cols_mega).sort_values(ascending=True)
fig = px.bar(x=feat_importances.values, y=feat_importances.index, orientation='h', labels={'x': 'Importance', 'y': 'Feature'}, title='AI 決策特徵重要性分析 (Feature Importance)')
fig.show()

print(f"🔥 20+ 複合特徵隨機森林準確率: {acc_mega:.2%}")
```
