"""
台股產業熱力圖 - 即時看板
自動每 60 秒刷新一次（交易時段內）

啟動方式:
    streamlit run streamlit_heatmap.py
"""

import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from twse_heatmap_realtime_and_history import (
    build_merged_data,
    get_hot_stocks,
    sector_heatmap_summary,
)

REFRESH_INTERVAL = 60  # 秒


def is_trading_hours() -> bool:
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    hour_min = now.hour * 100 + now.minute
    return (900 <= hour_min <= 1330)


def build_treemap(df: pd.DataFrame):
    fig = px.treemap(
        df,
        path=["產業別", "Name"],
        values="TradeValue",
        color="漲跌幅(%)",
        color_continuous_scale="RdYlGn_r",
        color_continuous_midpoint=0,
        title="台股類股熱力圖（大小=成交值，顏色=漲跌幅，紅漲綠跌）",
    )
    fig.update_layout(margin=dict(t=50, l=10, r=10, b=10), height=650)
    return fig


def build_sector_bar(df_summary: pd.DataFrame):
    colors = ["#d32f2f" if v > 0 else "#388e3c" for v in df_summary["加權平均漲跌幅(%)"]]
    fig = px.bar(
        df_summary,
        x="加權平均漲跌幅(%)",
        y="產業別",
        orientation="h",
        color="加權平均漲跌幅(%)",
        color_continuous_scale="RdYlGn_r",
        color_continuous_midpoint=0,
        title="各產業加權平均漲跌幅",
    )
    fig.update_layout(
        yaxis=dict(autorange="reversed"),
        height=max(400, len(df_summary) * 28),
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=False,
    )
    return fig


def main():
    st.set_page_config(page_title="台股熱力圖即時看板", page_icon="📈", layout="wide")
    st.title("📈 台股產業熱力圖即時看板")

    # 狀態指示
    trading = is_trading_hours()
    if trading:
        st.success(f"🟢 交易時段中 — 每 {REFRESH_INTERVAL} 秒自動更新")
    else:
        st.warning("🔴 非交易時段 — 顯示最近交易日資料，手動點按鈕更新")

    # 手動刷新按鈕
    if st.button("🔄 立即刷新", use_container_width=False):
        st.rerun()

    # 抓資料
    with st.spinner("正在抓取最新資料..."):
        try:
            df = build_merged_data()
        except Exception as e:
            st.error(f"資料抓取失敗：{e}")
            st.stop()

    # ---- 上方指標 ----
    total_stocks = len(df)
    up = (df["漲跌幅(%)"] > 0).sum()
    down = (df["漲跌幅(%)"] < 0).sum()
    flat = total_stocks - up - down
    total_value = df["TradeValue"].sum()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("上市股票數", f"{total_stocks} 檔")
    c2.metric("上漲 / 下漲 / 平盤", f"{up} / {down} / {flat}")
    c3.metric("總成交值", f"{total_value / 1e9:,.0f} 億")
    c4.metric("資料時間", datetime.now().strftime("%H:%M:%S"))

    st.divider()

    # ---- 主要視覺 ----
    tab_heatmap, tab_sector, tab_hot = st.tabs(["🗺️ Treemap 熱力圖", "📊 產業排行", "🔥 熱門股"])

    with tab_heatmap:
        fig = build_treemap(df)
        st.plotly_chart(fig, use_container_width=True)

    with tab_sector:
        summary = sector_heatmap_summary(df)
        fig_bar = build_sector_bar(summary)
        st.plotly_chart(fig_bar, use_container_width=True)
        st.dataframe(summary, use_container_width=True, hide_index=True)

    with tab_hot:
        top_col, sector_col = st.columns(2)
        with top_col:
            st.subheader("全市場熱門股 Top 20")
            hot = get_hot_stocks(df, by="成交值", top_n=20)
            st.dataframe(hot, use_container_width=True, hide_index=True)

        with sector_col:
            st.subheader("各產業熱門股 Top 5")
            sectors = sorted(df["產業別"].dropna().unique())
            sel = st.selectbox("選擇產業", sectors, index=0)
            hot_sector = get_hot_stocks(df[df["產業別"] == sel], by="成交值", top_n=5)
            st.dataframe(hot_sector, use_container_width=True, hide_index=True)

    # ---- 自動刷新 ----
    if trading:
        time.sleep(REFRESH_INTERVAL)
        st.rerun()


if __name__ == "__main__":
    main()
