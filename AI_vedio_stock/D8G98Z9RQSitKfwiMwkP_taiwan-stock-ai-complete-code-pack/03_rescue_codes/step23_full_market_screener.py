這是我準備好的 STEP 23 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# STEP 23: 分析程式碼重構為模組化 stock.py - 備用救援程式碼
import os

stock_analyzer_code = '''import pandas as pd
import numpy as np
import yfinance as yf
import requests
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
try:
    from google.colab import userdata
except ImportError:
    userdata = None

class StockAnalyzer:
    def __init__(self, ticker):
        self.ticker = ticker
        self.df = pd.DataFrame()  # 主要存放K線數據
        self.df_fin = pd.DataFrame() # 存放財報數據
        self.df_inst_pivot = pd.DataFrame() # 存放法人籌碼
        self.df_margin_data = pd.DataFrame() # 存放融資融券數據
        self.df_futures_data = pd.DataFrame() # 存放外資台指期數據
        self.df_securities_lending = pd.DataFrame() # 存放借券數據
        self.df_extended = pd.DataFrame() # 綜合所有K線和籌碼數據
        self.ml_df = pd.DataFrame() # 機器學習的基礎數據
        self.mega_df_cleaned_final = pd.DataFrame() # 最終特徵矩陣
        self.final_feature_cols = []
        self.finmind_token = userdata.get('FINMIND_TOKEN') if userdata else None

    def _fix_col_names(self, df_param: pd.DataFrame) -> pd.DataFrame:
        """根據指定邏輯清洗 DataFrame 的欄位名稱。"""
        if isinstance(df_param.columns, pd.MultiIndex):
            df_param.columns = [col[0].lower() for col in df_param.columns]
        else:
            df_param.columns = [col.lower() for col in df_param.columns]

        df_param.columns.name = None

        if 'adj close' in df_param.columns:
            df_param['close'] = df_param['adj close']
        elif 'adj close' in df_param.columns and 'close' not in df_param.columns:
            df_param = df_param.rename(columns={'adj close': 'close'})

        required_cols = ['open', 'high', 'low', 'close', 'volume']
        df_param = df_param[[col for col in required_cols if col in df_param.columns]]
        return df_param

    def _fetch_finmind_api_data(self, dataset, data_id, start_date, end_date, is_futures=False, is_securities_lending=False, use_mock_data=True):
        """統一處理 FinMind API 數據獲取和錯誤處理，支持模擬數據。"""
        url = "https://api.finmindtrade.com/api/v4/data"

        params = {
            "dataset": dataset,
            "data_id": data_id,
            "start_date": start_date,
            "end_date": end_date,
            "token": self.finmind_token
        }

        df_output = pd.DataFrame()

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status() # 檢查請求是否成功
            data = resp.json()

            if data.get('data'):
                df_output = pd.DataFrame(data['data'])
                df_output['date'] = pd.to_datetime(df_output['date'])
                df_output = df_output.set_index('date').sort_index()
                print(f"成功獲取 {dataset} 數據。")
            else:
                print(f"FinMind API 未回傳 {dataset} 數據，請檢查參數或 Token。將使用模擬數據。")
                if use_mock_data:
                    raise ValueError(f"No data from API for {dataset}")

        except (requests.exceptions.RequestException, ValueError) as e:
            print(f"獲取 {dataset} 數據時發生錯誤: {e}。將使用模擬數據。")
            if use_mock_data:
                # 生成模擬數據
                date_range = pd.date_range(start=start_date, end=end_date)
                if is_futures: # 台指期數據模擬
                    simulated_net_oi = np.random.randint(-15000, 15000, len(date_range))
                    df_output = pd.DataFrame({'Foreign_TX_Net_OI': simulated_net_oi}, index=date_range)
                elif is_securities_lending: # 借券賣出餘額數據模擬
                    simulated_sell_balance = np.random.randint(1000, 50000, len(date_range))
                    df_output = pd.DataFrame({'sell_balance': simulated_sell_balance}, index=date_range)
                else: # 融資融券數據模擬
                    simulated_margin_purchase = np.random.randint(15000, 35000, len(date_range))
                    simulated_short_sale = np.random.randint(500, 5000, len(date_range))
                    df_output = pd.DataFrame({
                        'stock_id': data_id,
                        'MarginPurchaseTodayBalance': simulated_margin_purchase,
                        'ShortSaleTodayBalance': simulated_short_sale
                    }, index=date_range)

        return df_output


    def fetch_data(self, period='3y'):
        """下載股票數據，並進行初步清洗與技術指標計算。"""
        print(f"\n--- STEP 1: 下載 {self.ticker} 股票數據 ({period}) ---")
        self.df = yf.download(self.ticker, period=period, progress=False)
        if self.df.empty:
            raise ValueError(f"無法取得 {self.ticker} 的股票數據。請檢查股票代號或時間區間。")

        self.df = self._fix_col_names(self.df)
        self.df.index = pd.to_datetime(self.df.index)

        # 計算均線 (MA5, MA20, MA60, MA120, MA240)
        self.df['ma5'] = self.df['close'].rolling(window=5).mean()
        self.df['ma20'] = self.df['close'].rolling(window=20).mean()
        self.df['ma60'] = self.df['close'].rolling(window=60).mean()
        self.df['ma120'] = self.df['close'].rolling(window=120).mean()
        self.df['ma240'] = self.df['close'].rolling(window=240).mean()

        # 計算 RSI(14)
        delta = self.df['close'].diff()
        gain = delta.where(delta > 0, 0)
        loss = (-delta).where(delta < 0, 0)
        avg_gain = gain.ewm(com=13, adjust=False).mean()
        avg_loss = loss.ewm(com=13, adjust=False).mean()
        rs = avg_gain / avg_loss
        self.df['rsi'] = 100 - (100 / (1 + rs))

        # 計算 MACD
        self.df['ema12'] = self.df['close'].ewm(span=12, adjust=False).mean()
        self.df['ema26'] = self.df['close'].ewm(span=26, adjust=False).mean()
        self.df['macd_line'] = self.df['ema12'] - self.df['ema26']
        self.df['signal_line'] = self.df['macd_line'].ewm(span=9, adjust=False).mean()
        self.df['macd_histogram'] = self.df['macd_line'] - self.df['signal_line']

        # 計算布林通道 (Bollinger Bands)
        window = 20
        self.df['middle_band'] = self.df['close'].rolling(window=window).mean()
        self.df['std_dev'] = self.df['close'].rolling(window=window).std()
        self.df['upper_band'] = self.df['middle_band'] + (self.df['std_dev'] * 2)
        self.df['lower_band'] = self.df['middle_band'] - (self.df['std_dev'] * 2)

        # 計算 ATR
        high_minus_low = self.df['high'] - self.df['low']
        high_minus_prev_close = abs(self.df['high'] - self.df['close'].shift(1))
        low_minus_prev_close = abs(self.df['low'] - self.df['close'].shift(1))
        self.df['tr'] = pd.concat([high_minus_low, high_minus_prev_close, low_minus_prev_close], axis=1).max(axis=1)
        self.df['atr'] = self.df['tr'].ewm(span=14, adjust=False).mean()

        print(f"成功下載並清洗 {self.ticker} 數據，並計算基礎技術指標。")

    def fetch_external_data(self):
        """獲取 FinMind 等外部數據，如法人籌碼、融資融券、期貨借券等。"""
        print("\n--- STEP 7: 獲取外部數據 (財報、法人籌碼、融資融券、期貨借券) ---")
        end_date = self.df.index.max()
        start_date_three_year = (end_date - pd.Timedelta(days=1095)).strftime('%Y-%m-%d')
        start_date_one_year = (end_date - pd.Timedelta(days=365)).strftime('%Y-%m-%d')
        str_end = end_date.strftime('%Y-%m-%d')

        # 財報數據
        ticker_yf = yf.Ticker(self.ticker)
        try:
            quarterly_financials = ticker_yf.quarterly_income_stmt
            if not quarterly_financials.empty:
                recent_financials_raw = quarterly_financials.iloc[:, :12]
                df_fin_transposed = recent_financials_raw.T
                total_revenue_col = 'Total Revenue'
                gross_profit_col = 'Gross Profit'
                cost_of_revenue_col = 'Cost Of Revenue'

                if total_revenue_col in df_fin_transposed.columns:
                    if gross_profit_col in df_fin_transposed.columns:
                        self.df_fin = df_fin_transposed[[total_revenue_col, gross_profit_col]].copy()
                    elif cost_of_revenue_col in df_fin_transposed.columns:
                        self.df_fin = df_fin_transposed[[total_revenue_col, cost_of_revenue_col]].copy()
                        self.df_fin[total_revenue_col] = pd.to_numeric(self.df_fin[total_revenue_col], errors='coerce')
                        self.df_fin[cost_of_revenue_col] = pd.to_numeric(self.df_fin[cost_of_revenue_col], errors='coerce')
                        self.df_fin[gross_profit_col] = self.df_fin[total_revenue_col] - self.df_fin[cost_of_revenue_col]
                    self.df_fin.index = pd.to_datetime(self.df_fin.index)
                    self.df_fin = self.df_fin.sort_index()
                    self.df_fin['GrossProfitMargin'] = (self.df_fin[gross_profit_col] / self.df_fin[total_revenue_col]) * 100
                    self.df_fin['GrossProfitMargin'] = self.df_fin['GrossProfitMargin'].replace([float('inf'), -float('inf')], pd.NA).fillna(pd.NA)
                print("成功獲取財報數據。")
            else:
                print("無法取得季度損益表數據。")
        except Exception as e:
            print(f"取得財報數據提示: {e}")

        # 法人買賣超
        clean_id = self.ticker.replace('.TW', '').replace('.TWO', '')
        df_inst = self._fetch_finmind_api_data(
            dataset="TaiwanStockInstitutionalInvestorsBuySell",
            data_id=clean_id,
            start_date=start_date_three_year,
            end_date=str_end
        )
        if not df_inst.empty and 'buy' in df_inst.columns and 'sell' in df_inst.columns:
            df_inst['net_buy_sell'] = df_inst['buy'] - df_inst['sell']
            df_inst_filtered = df_inst[df_inst['name'].isin(['Foreign_Investor', 'Investment_Trust'])].copy()
            if not df_inst_filtered.empty:
                self.df_inst_pivot = df_inst_filtered.reset_index().pivot_table(index='date', columns='name', values='net_buy_sell').fillna(0)
                self.df_inst_pivot = self.df_inst_pivot.rename(columns={
                    'Foreign_Investor': '外資累積買賣超',
                    'Investment_Trust': '投信累積買賣超'
                })
                if '外資累積買賣超' in self.df_inst_pivot.columns:
                    self.df_inst_pivot['外資累積買賣超'] = self.df_inst_pivot['外資累積買賣超'].cumsum()
                if '投信累積買賣超' in self.df_inst_pivot.columns:
                    self.df_inst_pivot['投信累積買賣超'] = self.df_inst_pivot['投信累積買賣超'].cumsum()

        # 融資融券數據
        self.df_margin_data = self._fetch_finmind_api_data(
            dataset="TaiwanStockMarginPurchaseShortSale",
            data_id=clean_id,
            start_date=start_date_three_year,
            end_date=str_end
        )
        if not self.df_margin_data.empty and 'ShortSaleTodayBalance' in self.df_margin_data.columns and 'MarginPurchaseTodayBalance' in self.df_margin_data.columns:
            self.df_margin_data['short_margin_ratio'] = self.df_margin_data['ShortSaleTodayBalance'] / self.df_margin_data['MarginPurchaseTodayBalance']
            self.df_margin_data['short_margin_ratio'] = self.df_margin_data['short_margin_ratio'].replace([np.inf, -np.inf], np.nan).fillna(0)

        # 外資台指期法人數據
        self.df_futures_data = self._fetch_finmind_api_data(
            dataset="TaiwanFuturesInstitutionalInvestors",
            data_id="TX",
            start_date=start_date_one_year,
            end_date=str_end,
            is_futures=True
        )
        if not self.df_futures_data.empty and 'institutional_investors' in self.df_futures_data.columns:
            df_foreign_futures = self.df_futures_data[self.df_futures_data['institutional_investors'] == '外資'].copy()
            self.df_futures_data = pd.DataFrame(index=df_foreign_futures.index)
            self.df_futures_data['Foreign_TX_Net_OI'] = df_foreign_futures['long_open_interest_balance_volume'] - df_foreign_futures['short_open_interest_balance_volume']

        # 借券賣出餘額
        self.df_securities_lending = self._fetch_finmind_api_data(
            dataset="TaiwanStockSecuritiesLending",
            data_id=clean_id,
            start_date=start_date_one_year,
            end_date=str_end,
            is_securities_lending=True
        )
        if not self.df_securities_lending.empty and 'volume' in self.df_securities_lending.columns:
            self.df_securities_lending = self.df_securities_lending.groupby('date')['volume'].sum().to_frame(name='sell_balance')

        print("外部數據獲取完成。")

    def engineer_features(self):
        """結合所有數據，建構 AI 模型所需的複合特徵矩陣。"""
        print("\n--- STEP 8: 建構複合特徵矩陣 ---")

        self.df_extended = self.df.copy()

        # 合併法人買賣超
        if not self.df_inst_pivot.empty:
            self.df_extended = pd.merge(
                self.df_extended,
                self.df_inst_pivot,
                left_index=True,
                right_index=True,
                how='left'
            )

        # 合併融資融券
        if not self.df_margin_data.empty:
            cols = [c for c in ['MarginPurchaseTodayBalance', 'ShortSaleTodayBalance', 'short_margin_ratio'] if c in self.df_margin_data.columns]
            self.df_extended = pd.merge(
                self.df_extended,
                self.df_margin_data[cols],
                left_index=True,
                right_index=True,
                how='left'
            )

        # 合併外資台指期
        if not self.df_futures_data.empty:
            self.df_extended = pd.merge(
                self.df_extended,
                self.df_futures_data[['Foreign_TX_Net_OI']],
                left_index=True,
                right_index=True,
                how='left'
            )

        # 合併借券
        if not self.df_securities_lending.empty:
            self.df_extended = pd.merge(
                self.df_extended,
                self.df_securities_lending[['sell_balance']],
                left_index=True,
                right_index=True,
                how='left'
            )

        self.df_extended = self.df_extended.ffill().fillna(0)
        self.ml_df = self.df_extended.copy()

        # 基礎技術特徵
        self.ml_df['Bias_20'] = ((self.ml_df['close'] - self.ml_df['ma20']) / self.ml_df['ma20']) * 100
        self.ml_df['Daily_Return'] = self.ml_df['close'].pct_change() * 100
        self.ml_df['RSI'] = self.ml_df['rsi']

        # 動能特徵
        self.ml_df['Daily_Return_1d'] = self.ml_df['close'].pct_change(periods=1) * 100
        self.ml_df['Daily_Return_3d'] = self.ml_df['close'].pct_change(periods=3) * 100
        self.ml_df['Daily_Return_5d'] = self.ml_df['close'].pct_change(periods=5) * 100
        self.ml_df['MACD_Histogram'] = self.ml_df['macd_histogram']

        # 波動率與型態
        self.ml_df['BB_Width'] = ((self.ml_df['upper_band'] - self.ml_df['lower_band']) / self.ml_df['middle_band']) * 100
        self.ml_df['Normalized_ATR'] = (self.ml_df['atr'] / self.ml_df['close'] * 100)

        # 跨市場特徵
        cross_market_tickers = {'^SOX': 'SOX_Change', '^TNX': 'TNX_Change', '^VIX': 'VIX_Change'}
        for ticker, col_name in cross_market_tickers.items():
            try:
                cross_market_data = yf.download(ticker, period='3y', progress=False)
                if not cross_market_data.empty:
                    close_col = cross_market_data['Close'] if 'Close' in cross_market_data.columns else cross_market_data.iloc[:, 0]
                    self.ml_df[col_name] = close_col.pct_change() * 100
                    self.ml_df[col_name] = self.ml_df[col_name].reindex(self.ml_df.index, method='ffill').fillna(0)
                else:
                    self.ml_df[col_name] = 0.0
            except Exception:
                self.ml_df[col_name] = 0.0

        # Lead-Lag 領先特徵
        lag_periods = [1, 3, 5]
        for col in ['Foreign_TX_Net_OI', 'sell_balance']:
            if col in self.ml_df.columns:
                for lag in lag_periods:
                    self.ml_df[f'{col}_Lag{lag}'] = self.ml_df[col].shift(lag)

        # 標籤工程
        self.ml_df['Next_Close'] = self.ml_df['close'].shift(-1)
        self.ml_df['Target'] = (self.ml_df['Next_Close'] > self.ml_df['close']).astype(int)

        self.mega_df_cleaned_final = self.ml_df.dropna()

        potential_cols = [
            'Bias_20', 'Daily_Return', 'RSI', 'Foreign_TX_Net_OI', 'sell_balance',
            'Daily_Return_1d', 'Daily_Return_3d', 'Daily_Return_5d', 'MACD_Histogram',
            'BB_Width', 'Normalized_ATR', 'SOX_Change', 'TNX_Change', 'VIX_Change',
            'Foreign_TX_Net_OI_Lag1', 'Foreign_TX_Net_OI_Lag3', 'Foreign_TX_Net_OI_Lag5',
            'sell_balance_Lag1', 'sell_balance_Lag3', 'sell_balance_Lag5'
        ]
        self.final_feature_cols = [col for col in potential_cols if col in self.mega_df_cleaned_final.columns]

        print("複合特徵矩陣建構完成。")


    def run_ai_analysis(self):
        """訓練 AI 模型並進行回測。"""
        print("\n--- STEP 9: 運行 AI 模型分析與回測 ---")
        if self.mega_df_cleaned_final.empty or 'Target' not in self.mega_df_cleaned_final.columns:
            print("錯誤：特徵矩陣為空或缺少 'Target' 欄位，無法進行 AI 分析。")
            return

        X = self.mega_df_cleaned_final[self.final_feature_cols]
        y = self.mega_df_cleaned_final['Target']

        if len(X) < 2:
            print("錯誤：數據點不足，無法分割訓練集和測試集並訓練模型。")
            return

        test_size = 0.2 if len(X) > 5 else 0.5
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, shuffle=False)

        model = RandomForestClassifier(n_estimators=200, random_state=42)
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        print(f"模型在測試集上的準確度: {accuracy:.2f}")

        # 回測部分
        backtest_df = pd.DataFrame(index=X_test.index)
        backtest_df['Daily_Return'] = self.mega_df_cleaned_final.loc[X_test.index, 'Daily_Return']
        backtest_df['Signal'] = y_pred

        backtest_df['Strategy_Raw_Return'] = backtest_df['Signal'].shift(1) * backtest_df['Daily_Return']
        backtest_df['Buy_Hold_Return'] = backtest_df['Daily_Return']

        position_change = backtest_df['Signal'].shift(1).diff().abs()
        transaction_cost_per_trade = 0.003
        backtest_df['Transaction_Cost'] = position_change * transaction_cost_per_trade * 100
        backtest_df['Strategy_Net_Return'] = backtest_df['Strategy_Raw_Return'] - backtest_df['Transaction_Cost'].fillna(0)

        backtest_df['Buy_Hold_Cumulative'] = (1 + backtest_df['Buy_Hold_Return'].fillna(0) / 100).cumprod()
        backtest_df['Strategy_Cumulative'] = (1 + backtest_df['Strategy_Net_Return'].fillna(0) / 100).cumprod()

        final_buy_hold_return = (backtest_df['Buy_Hold_Cumulative'].iloc[-1] - 1) * 100 if not backtest_df.empty else 0
        final_strategy_return = (backtest_df['Strategy_Cumulative'].iloc[-1] - 1) * 100 if not backtest_df.empty else 0

        print(f"買進持有最終累積總報酬率: {final_buy_hold_return:.2f}%")
        print(f"AI 策略最終累積總報酬率 (含成本): {final_strategy_return:.2f}%")

        feature_importances = model.feature_importances_
        feature_importance_df = pd.DataFrame({
            'Feature': X_train.columns,
            'Importance': feature_importances
        }).sort_values(by='Importance', ascending=False)
        print("\n特徵重要性 (Top 5):")
        print(feature_importance_df.head())

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Buy_Hold_Cumulative'], mode='lines', name='買進持有', line=dict(color='blue', width=2)))
        fig.add_trace(go.Scatter(x=backtest_df.index, y=backtest_df['Strategy_Cumulative'], mode='lines', name='AI 策略 (含成本)', line=dict(color='red', width=2)))
        fig.update_layout(
            title_text=f"{self.ticker} 買進持有 vs. AI 策略累積報酬率對比",
            template='plotly_white',
            xaxis_title="日期",
            yaxis_title="累積淨值",
            xaxis_rangeslider_visible=False
        )
        fig.show()

if __name__ == '__main__':
    try:
        analyzer = StockAnalyzer('2330.TW')
        analyzer.fetch_data(period='3y')
        analyzer.fetch_external_data()
        analyzer.engineer_features()
        analyzer.run_ai_analysis()
    except Exception as e:
        print(f"執行提示: {e}")
'''

# 寫入 stock.py 檔案
with open('stock.py', 'w', encoding='utf-8') as f:
    f.write(stock_analyzer_code)

print("=" * 60)
print(f"✅ stock.py 模組化檔案已成功自動建立！路徑：{os.path.abspath('stock.py')}")
print("=" * 60)

# 嘗試啟動瀏覽器自動下載 (支援 Google Colab 環境)
try:
    from google.colab import files
    print("🚀 正在啟動瀏覽器自動下載 stock.py...")
    files.download('stock.py')
    print("📥 下載指令已送出！請檢查您電腦瀏覽器的「下載」資料夾。")
except Exception as e:
    print(f"💡 瀏覽器自動下載提示 (若未自動跳出): {e}")

print("\n📂 【手動下載備用指引】：")
print("👉 您也可以隨時點擊 Colab 左側面板的「📁 檔案」圖示")
print("👉 在檔案列表中找到 stock.py，按右鍵點選「下載」即可存至本機電腦！")
print("\n🎉 STEP 23 完成！stock.py 與 requirements.txt 已備妥，可進行 STEP 24 Hugging Face 線上部署！")
```
