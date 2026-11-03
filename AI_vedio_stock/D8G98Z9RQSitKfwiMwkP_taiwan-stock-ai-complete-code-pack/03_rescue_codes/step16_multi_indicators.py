這是我準備好的 STEP 16 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# STEP 16: 訓練 AI 模型 (破解勝率迷思) - 備用救援程式碼
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import pandas as pd
import numpy as np
import yfinance as yf

# 確保前置變數存在
if 'df' not in globals() or df.empty:
    df = yf.download('2330.TW', period='3y', auto_adjust=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = [col.lower() for col in df.columns]

if 'ma20' not in df.columns:
    df['ma20'] = df['close'].rolling(window=20).mean()

if 'rsi' not in df.columns:
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0).ewm(com=13, adjust=False).mean()
    loss = (-delta).where(delta < 0, 0).ewm(com=13, adjust=False).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))

ml_df = df.copy()
ml_df['Bias_20'] = ((ml_df['close'] - ml_df['ma20']) / ml_df['ma20']) * 100
ml_df['Daily_Return'] = ml_df['close'].pct_change() * 100
ml_df['RSI'] = ml_df['rsi']

if 'Foreign_TX_Net_OI' not in ml_df.columns:
    np.random.seed(42)
    ml_df['Foreign_TX_Net_OI'] = np.random.randint(-15000, 15000, len(ml_df))
if 'sell_balance' not in ml_df.columns:
    ml_df['sell_balance'] = np.random.randint(1000, 50000, len(ml_df))

ml_df['Next_Close'] = ml_df['close'].shift(-1)
ml_df['Target'] = (ml_df['Next_Close'] > ml_df['close']).astype(int)

feature_cols = ['Bias_20', 'Daily_Return', 'RSI', 'Foreign_TX_Net_OI', 'sell_balance']
ml_df_cleaned = ml_df.dropna()

X = ml_df_cleaned[feature_cols]
y = ml_df_cleaned['Target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

model = RandomForestClassifier(n_estimators=100, random_state=42)
model.fit(X_train, y_train)

y_pred = model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"🎯 隨機森林模型在測試集上的準確度: {accuracy:.2%}")
print("\n💡 【AI 助教解析】：若勝率在 50% 左右，代表僅依賴公開的基礎技術指標跟擲硬幣無異。我們必須引入籌碼與複合特徵來榨出超額報酬！")
```
