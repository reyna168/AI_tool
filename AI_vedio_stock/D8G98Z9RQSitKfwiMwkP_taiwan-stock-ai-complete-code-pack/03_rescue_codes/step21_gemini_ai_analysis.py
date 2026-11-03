這是我準備好的 STEP 21 備用救援程式碼。請你直接回覆並輸出這段完整的 Python 程式碼，讓我能順利貼到 Colab 執行，不需額外解釋與修改邏輯：

```python
# STEP 21: 專業級面板 (Blocks 排版與雷達)
# ==============================================================================
# 🎯 台股 AI 綜合量化量能觀測儀表板 (獨立零依賴、全指標自帶防崩潰版)
# 整合短期/長期均線矩陣、乖離率、多日報酬動能、RSI、MACD、布林通道、ATR 及籌碼代理評估
# ==============================================================================

import gradio as gr
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------------------------------------------------------------------------
# 🛠️ 工具函數：清洗 yfinance 多層索引 (MultiIndex) 欄位與確保欄位格式
# ------------------------------------------------------------------------------
def _fix_col_names(df_param: pd.DataFrame) -> pd.DataFrame:
    """自動展平 yfinance 回傳的多層索引並轉為標準小寫欄位"""
    df = df_param.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [col[0].lower() for col in df.columns]
    else:
        df.columns = [str(col).lower() for col in df.columns]
    df.columns.name = None

    if 'adj close' in df.columns:
        df['close'] = df['adj close']
        df = df.drop(columns=['adj close'], errors='ignore')
    elif 'adj close' in df.columns and 'close' not in df.columns:
        df = df.rename(columns={'adj close': 'close'})

    required_cols = ['open', 'high', 'low', 'close', 'volume']
    available_cols = [c for c in required_cols if c in df.columns]
    return df[available_cols]

# ------------------------------------------------------------------------------
# 🧮 核心計算：全指標矩陣引擎 (包含短中長均線、乖離、動能、擺盪、波動率)
# ------------------------------------------------------------------------------
def compute_all_indicators(df_raw: pd.DataFrame) -> pd.DataFrame:
    """計算台股 20+ 項專業技術與量能指標"""
    df = df_raw.copy()

    # 1. 均線矩陣 (短中長期完整排列)
    df['ma5'] = df['close'].rolling(5).mean()
    df['ma10'] = df['close'].rolling(10).mean()
    df['ma20'] = df['close'].rolling(20).mean()
    df['ma60'] = df['close'].rolling(60).mean()
    df['ma120'] = df['close'].rolling(120).mean()
    df['ma240'] = df['close'].rolling(240).mean()

    # 2. 乖離率 (BIAS)
    df['bias_5'] = ((df['close'] - df['ma5']) / df['ma5']) * 100
    df['bias_20'] = ((df['close'] - df['ma20']) / df['ma20']) * 100

    # 3. 累積動能報酬率 (1d / 3d / 5d)
    df['ret_1d'] = df['close'].pct_change(1) * 100
    df['ret_3d'] = df['close'].pct_change(3) * 100
    df['ret_5d'] = df['close'].pct_change(5) * 100

    # 4. RSI (14日相對強弱指標)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(com=13, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(com=13, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))

    # 5. MACD (DIF, DEM, 柱狀體)
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['macd_dif'] = ema12 - ema26
    df['macd_dem'] = df['macd_dif'].ewm(span=9, adjust=False).mean()
    df['macd_hist'] = df['macd_dif'] - df['macd_dem']

    # 6. 布林通道 (Bollinger Bands & BB Width)
    df['bb_mid'] = df['ma20']
    df['bb_std'] = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_mid'] + (df['bb_std'] * 2)
    df['bb_lower'] = df['bb_mid'] - (df['bb_std'] * 2)
    df['bb_width'] = ((df['bb_upper'] - df['bb_lower']) / df['bb_mid'].replace(0, np.nan)) * 100

    # 7. ATR (14日真實波幅與停損建議)
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift()).abs()
    low_close = (df['low'] - df['close'].shift()).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['atr_14'] = tr.ewm(com=13, adjust=False).mean()

    # 8. 量能均線 (Vol MA5 / MA20)
    df['vol_ma5'] = df['volume'].rolling(5).mean()
    df['vol_ma20'] = df['volume'].rolling(20).mean()

    return df

# ------------------------------------------------------------------------------
# 📊 核心分析函數：單檔技術與量能視覺化診斷 (含多層圖表與完整指標診斷表)
# ------------------------------------------------------------------------------
def analyze_stock(ticker: str, period: str):
    """
    下載指定標的歷史數據、計算全方位量化指標、繪製四層 Plotly 圖表並產出診斷報表
    """
    if not ticker or not ticker.strip():
        return go.Figure(), "⚠️ 請輸入有效的台股代號（例如: 2330.TW 或 2317）", pd.DataFrame()

    ticker_clean = ticker.strip().upper()
    if not (ticker_clean.endswith(".TW") or ticker_clean.endswith(".TWO") or "^" in ticker_clean):
        ticker_clean += ".TW"

    try:
        # 下載股票歷史數據 (自動關閉 auto_adjust 以保留標準原始價格)
        df_raw = yf.download(ticker_clean, period=period, progress=False, auto_adjust=False)
        if df_raw.empty or len(df_raw) < 5:
            return go.Figure(), f"❌ 無法取得【{ticker_clean}】的歷史數據，請確認代號是否正確或市場休市中。", pd.DataFrame()

        df = _fix_col_names(df_raw)
        df.index = pd.to_datetime(df.index)
        df = compute_all_indicators(df)

        latest = df.iloc[-1]

        # ----------------------------------------------------------------------
        # 🎨 建構 Plotly 4 層全景量化圖表
        # ----------------------------------------------------------------------
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.48, 0.16, 0.18, 0.18],
            subplot_titles=(
                f"📈 {ticker_clean} K線走勢、均線矩陣 (MA5/20/60) 與布林通道",
                "⚡ RSI(14) 動能擺盪指標",
                "📊 MACD 雙均線差離與紅綠柱狀體",
                "📦 成交量與 ATR(14) 波動區間"
            )
        )

        # Layer 1: K線 + 均線 + 布林帶
        fig.add_trace(go.Candlestick(
            x=df.index, open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            name="K線", increasing_line_color="#ef4444", decreasing_line_color="#22c55e"
        ), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ma5'], line=dict(color='#f59e0b', width=1.2), name='MA5(週線)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ma20'], line=dict(color='#3b82f6', width=1.6), name='MA20(月線)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['ma60'], line=dict(color='#8b5cf6', width=1.4), name='MA60(季線)'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_upper'], line=dict(color='rgba(156,163,175,0.6)', dash='dash'), name='布林上軌'), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['bb_lower'], line=dict(color='rgba(156,163,175,0.6)', dash='dash'), name='布林下軌'), row=1, col=1)

        # Layer 2: RSI
        fig.add_trace(go.Scatter(x=df.index, y=df['rsi_14'], line=dict(color='#ec4899', width=1.5), name='RSI(14)'), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#22c55e", row=2, col=1)

        # Layer 3: MACD
        hist_colors = ['#ef4444' if (v or 0) >= 0 else '#22c55e' for v in df['macd_hist']]
        fig.add_trace(go.Bar(x=df.index, y=df['macd_hist'], marker_color=hist_colors, name='MACD柱狀體'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['macd_dif'], line=dict(color='#f97316', width=1.2), name='DIF快線'), row=3, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['macd_dem'], line=dict(color='#06b6d4', width=1.2), name='DEM慢線'), row=3, col=1)

        # Layer 4: Volume & ATR
        vol_colors = ['#ef4444' if df['close'].iloc[i] >= df['open'].iloc[i] else '#22c55e' for i in range(len(df))]
        fig.add_trace(go.Bar(x=df.index, y=df['volume'], marker_color=vol_colors, opacity=0.4, name='成交量'), row=4, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=df['vol_ma5'], line=dict(color='#eab308', width=1.1), name='5日均量'), row=4, col=1)

        fig.update_layout(
            height=850,
            template="plotly_white",
            xaxis_rangeslider_visible=False,
            margin=dict(l=30, r=30, t=40, b=30),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        # ----------------------------------------------------------------------
        # 📋 產生結構化全指標診斷表 (符合多空量化矩陣)
        # ----------------------------------------------------------------------
        close_p = latest['close']
        ma5_p = latest['ma5']
        ma20_p = latest['ma20']
        ma60_p = latest['ma60']
        bias20_v = latest['bias_20']
        rsi_v = latest['rsi_14']
        macd_h = latest['macd_hist']
        bb_w = latest['bb_width']
        atr_v = latest['atr_14']
        suggested_stop = close_p - (atr_v * 1.5)

        sig_ma_short = "⬆️ 偏多" if (close_p > ma20_p and ma5_p > ma20_p) else "⬇️ 偏空" if (close_p < ma20_p) else "➖ 中立"
        sig_ma_long = "⬆️ 偏多" if (pd.notna(ma60_p) and close_p > ma60_p) else "➖ 中立"
        sig_bias = "⚠️ 超買乖離" if bias20_v > 8 else "🟢 超賣反彈" if bias20_v < -8 else "➖ 常態區間"
        sig_ret = "⬆️ 動能推升" if (latest['ret_1d'] > 0 and latest['ret_3d'] > 0) else "⬇️ 動能趨緩"
        sig_rsi = "🔥 處超買區 (>70)" if rsi_v > 70 else "❄️ 處超賣區 (<30)" if rsi_v < 30 else "⬆️ 多方主控" if rsi_v >= 50 else "⬇️ 空方主控"
        sig_macd = "⬆️ 紅柱多頭進攻" if macd_h > 0 else "⬇️ 綠柱空頭承壓"
        sig_bb = "🚀 帶寬擴張發散" if bb_w > 8 else "➖ 帶寬壓縮盤整"

        report_table_data = [
            {"指標名稱": "MA5 / MA10 / MA20 (短中期均線)", "類別": "均線與趨勢", "即時數值": f"{latest['ma5']:.1f} / {latest['ma10']:.1f} / {latest['ma20']:.1f}", "多空訊號": sig_ma_short, "策略意義": "月線之上維持多頭排列" if sig_ma_short == "⬆️ 偏多" else "跌破月線轉為整理"},
            {"指標名稱": "MA60 / MA120 / MA240 (長期均線矩陣)", "類別": "均線與趨勢", "即時數值": f"{latest['ma60']:.1f} / {latest.get('ma120', np.nan):.1f} / {latest.get('ma240', np.nan):.1f}", "多空訊號": sig_ma_long, "策略意義": "季線強固多頭支撐" if sig_ma_long == "⬆️ 偏多" else "中長期均線橫向糾結"},
            {"指標名稱": "20日乖離率 (Bias 20)", "類別": "動能與擺盪", "即時數值": f"{bias20_v:+.2f}%", "多空訊號": sig_bias, "策略意義": "處於合理安全常態範圍" if sig_bias == "➖ 常態區間" else "留意正負乖離過大之拉回風險"},
            {"指標名稱": "1d / 3d / 5d 累積報酬率", "類別": "動能與擺盪", "即時數值": f"{latest['ret_1d']:+.2f}% / {latest['ret_3d']:+.2f}% / {latest['ret_5d']:+.2f}%", "多空訊號": sig_ret, "策略意義": "短線多方動能連續推進" if sig_ret == "⬆️ 動能推升" else "短線出現震盪調節"},
            {"指標名稱": "RSI (14) 相對強弱指標", "類別": "動能與擺盪", "即時數值": f"{rsi_v:.1f}", "多空訊號": sig_rsi, "策略意義": "多方主控進攻區間" if rsi_v >= 50 else "空方主導偏弱震盪"},
            {"指標名稱": "MACD (DIF / DEM / 柱狀體)", "類別": "動能與擺盪", "即時數值": f"{latest['macd_dif']:.2f} / {latest['macd_dem']:.2f} / {macd_h:+.2f}", "多空訊號": sig_macd, "策略意義": "紅柱放大 偏多進攻" if macd_h > 0 else "綠柱延伸 偏空整理"},
            {"指標名稱": "布林通道帶寬 (BB Width)", "類別": "波動與型態", "即時數值": f"{bb_w:.2f}%", "多空訊號": sig_bb, "策略意義": "喇叭開口 趨勢行情展開中" if bb_w > 8 else "通道壓縮 醞釀突破方向"},
            {"指標名稱": "ATR (14) 真實波幅停損建議", "類別": "波動與型態", "即時數值": f"{atr_v:.2f} 元 ({(atr_v/close_p)*100:.2f}%)", "多空訊號": "➖ 風控參考", "策略意義": f"動態追蹤停損建議設於 {suggested_stop:.2f} 元"}
        ]
        report_df = pd.DataFrame(report_table_data)

        # 診斷摘要文字
        summary_markdown = f"""### 🎯 【{ticker_clean}】最新量化多空深度總評
- **最新收盤價**：`{close_p:.2f}` 元 ｜ **單日漲跌**：`{latest['ret_1d']:+.2f}%` ｜ **成交量**：`{int(latest['volume']):,}` 股
- **核心均線 (MA20 月線)**：`{ma20_p:.2f}` 元 ｜ **月線乖離率**：`{bias20_v:+.2f}%`
- **動能擺盪**：RSI(14) 為 `{rsi_v:.1f}`，MACD 柱狀體為 `{macd_h:+.2f}`（{sig_macd}）
- **風控停損點**：依據 ATR(14) 計算，防守關鍵點建議設於 **`{suggested_stop:.2f}` 元**
"""
        return fig, summary_markdown, report_df

    except Exception as e:
        return go.Figure(), f"⚠️ 分析過程發生未預期錯誤：{str(e)}", pd.DataFrame()

# ------------------------------------------------------------------------------
# 🎯 自選股雷達函數：批次多股掃描 (含收盤價、漲跌幅、MA20、RSI、多空訊號)
# ------------------------------------------------------------------------------
def scan_watchlist(watchlist_str: str) -> pd.DataFrame:
    """
    掃描多檔自選股，計算並彙整關鍵指標，產出結構化雷達看板
    """
    if not watchlist_str or not watchlist_str.strip():
        return pd.DataFrame(columns=['股票代號', '最新收盤價', '單日漲跌幅', 'MA20(月線)', '20日乖離率', 'RSI(14)', '多空評定'])

    raw_symbols = [s.strip().upper() for s in watchlist_str.replace("，", ",").split(",") if s.strip()]
    results = []

    for sym in raw_symbols:
        ticker = sym if (sym.endswith(".TW") or sym.endswith(".TWO") or "^" in sym) else f"{sym}.TW"
        try:
            df_raw = yf.download(ticker, period="3mo", progress=False, auto_adjust=False)
            if df_raw.empty or len(df_raw) < 20:
                continue

            df = _fix_col_names(df_raw)
            close = float(df['close'].iloc[-1])
            prev_close = float(df['close'].iloc[-2]) if len(df) > 1 else close
            change_pct = ((close - prev_close) / prev_close) * 100

            ma20 = float(df['close'].rolling(20).mean().iloc[-1])
            bias20 = ((close - ma20) / ma20) * 100

            # RSI(14)
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).ewm(com=13, adjust=False).mean()
            loss = (-delta.where(delta < 0, 0)).ewm(com=13, adjust=False).mean()
            rs = gain / loss.replace(0, np.nan)
            rsi = float((100 - (100 / (1 + rs))).iloc[-1])

            # 多空訊號綜合評定
            if close > ma20 and bias20 > 0 and rsi >= 50:
                signal = "🔥 多頭強勢"
            elif close < ma20 and bias20 < 0 and rsi < 50:
                signal = "❄️ 空頭弱勢"
            else:
                signal = "➖ 震盪整理"

            results.append({
                "股票代號": sym,
                "最新收盤價": f"{close:.2f}",
                "單日漲跌幅": f"{change_pct:+.2f}%",
                "MA20(月線)": f"{ma20:.2f}",
                "20日乖離率": f"{bias20:+.2f}%",
                "RSI(14)": f"{rsi:.1f}",
                "多空評定": signal
            })
        except Exception:
            continue

    if not results:
        return pd.DataFrame(columns=['股票代號', '最新收盤價', '單日漲跌幅', 'MA20(月線)', '20日乖離率', 'RSI(14)', '多空評定'])

    return pd.DataFrame(results)

# ------------------------------------------------------------------------------
# 🚀 Gradio Blocks 現代化 UI 介面架構
# ------------------------------------------------------------------------------
with gr.Blocks(theme=gr.themes.Soft(), title="台股 AI 綜合量化量能觀測儀表板") as app:
    gr.Markdown("# 📈 台股 AI 綜合量化量能觀測儀表板")
    gr.Markdown("結合 **短中長均線矩陣、動能加速指標、RSI / MACD / 布林通道、ATR 風控波幅** 之全方位視覺化看盤系統。")

    with gr.Tabs():
        # Tab 1: 單檔技術與模型透視
        with gr.TabItem("📊 單檔技術與模型透視"):
            with gr.Row():
                with gr.Column(scale=1):
                    ticker_input = gr.Dropdown(
                        label="選擇熱門股或手動輸入股票代號 (如: 2330.TW)",
                        choices=["2330.TW", "2317.TW", "2454.TW", "2303.TW", "2308.TW", "2603.TW", "^TWII"],
                        value="2330.TW",
                        allow_custom_value=True,
                        interactive=True
                    )
                    period_input = gr.Dropdown(
                        label="歷史分析區間",
                        choices=["1mo", "3mo", "6mo", "1y", "2y", "3y", "5y"],
                        value="1y"
                    )
                    analyze_btn = gr.Button("🚀 啟動量化綜合分析", variant="primary")

                with gr.Column(scale=2):
                    summary_output = gr.Markdown("請點擊左側【啟動量化綜合分析】按鈕以載入盤勢數據...")

            plot_output = gr.Plot(label="Plotly 4層全景量化走勢圖")

            gr.Markdown("### 📋 全方位量化指標多空診斷矩陣")
            table_output = gr.DataFrame(label="即時指標數據與策略解讀", interactive=False)

            analyze_btn.click(
                fn=analyze_stock,
                inputs=[ticker_input, period_input],
                outputs=[plot_output, summary_output, table_output],
                concurrency_limit=10
            )

        # Tab 2: 智慧自選股雷達
        with gr.TabItem("🎯 智慧自選股雷達"):
            with gr.Row():
                watchlist_input = gr.Textbox(
                    label="輸入自選股票清單 (以逗號分隔)",
                    value="2330, 2317, 2454, 2303, 2308, 3231, 2603, 0050",
                    lines=2
                )
                scan_btn = gr.Button("🔍 啟動多股即時雷達掃描", variant="primary")

            radar_output = gr.DataFrame(label="自選股即時量化雷達矩陣", interactive=False)

            scan_btn.click(
                fn=scan_watchlist,
                inputs=[watchlist_input],
                outputs=[radar_output],
                concurrency_limit=5
            )

if __name__ == "__main__":
    app.launch(share=True)
```
