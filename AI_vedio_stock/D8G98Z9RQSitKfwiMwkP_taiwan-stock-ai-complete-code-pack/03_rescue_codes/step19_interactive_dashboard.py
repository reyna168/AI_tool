這是我準備好的 STEP 19 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# STEP 19: 構建量化分析腳本 (自動化) - 備用救援程式碼
import pandas as pd
import numpy as np
import yfinance as yf
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

class StockAnalyzer:
    def __init__(self, ticker='2330.TW', period='3y'):
        self.ticker = ticker
        self.period = period
        self.df = pd.DataFrame()
        self.mega_df = pd.DataFrame()
        self.model = None

    def fetch_data(self):
        print(f"📥 正在下載 {self.ticker} 資料 ({self.period})...")
        raw = yf.download(self.ticker, period=self.period, progress=False, auto_adjust=False)
        if isinstance(raw.columns, pd.MultiIndex):
            raw.columns = [c[0].lower() for c in raw.columns]
        else:
            raw.columns = [c.lower() for c in raw.columns]
        if 'adj close' in raw.columns:
            raw['close'] = raw['adj close']
            raw.drop(columns=['adj close'], inplace=True, errors='ignore')
        self.df = raw[['open', 'high', 'low', 'close', 'volume']].copy()
        return self

    def engineer_features(self):
        df = self.df.copy()
        df['ma5'] = df['close'].rolling(5).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        df['bias_20'] = ((df['close'] - df['ma20']) / df['ma20']) * 100
        df['ret_1d'] = df['close'].pct_change(1) * 100
        df['ret_3d'] = df['close'].pct_change(3) * 100
        df['ret_5d'] = df['close'].pct_change(5) * 100

        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).ewm(com=13, adjust=False).mean()
        loss = (-delta).where(delta < 0, 0).ewm(com=13, adjust=False).mean()
        df['rsi'] = 100 - (100 / (1 + (gain / loss)))

        df['Next_Close'] = df['close'].shift(-1)
        df['Target'] = (df['Next_Close'] > df['close']).astype(int)
        self.mega_df = df.dropna()
        return self

    def run_ai_analysis(self):
        features = ['bias_20', 'ret_1d', 'ret_3d', 'ret_5d', 'rsi']
        X = self.mega_df[features]
        y = self.mega_df['Target']
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)
        self.model = RandomForestClassifier(n_estimators=100, random_state=42)
        self.model.fit(X_train, y_train)
        acc = accuracy_score(y_test, self.model.predict(X_test))
        print(f"✅ {self.ticker} 自動化分析完成！模型準確率: {acc:.2%}")
        return acc

# 實例化並執行
analyzer = StockAnalyzer('2330.TW', '3y')
analyzer.fetch_data().engineer_features().run_ai_analysis()
```
