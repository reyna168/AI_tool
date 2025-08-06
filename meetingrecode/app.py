import streamlit as st
import json

# 載入問答資料
with open("qa_data.json", "r", encoding="utf-8") as f:
    qa_data = json.load(f)

st.set_page_config(page_title="系統 Q&A 詢問站", layout="wide")

st.title("🔍 新系統測試與流程 Q&A")
st.write("根據 2025/8/1 會議紀錄，以下提供常見問答搜尋")

# 選擇分類
categories = sorted(set(q["category"] for q in qa_data))
selected_category = st.selectbox("📁 選擇主題分類", ["全部"] + categories)

# 搜尋欄
query = st.text_input("🔎 搜尋關鍵字（例如：打卡、請假、報價單）")

# 篩選條件
filtered_data = qa_data
if selected_category != "全部":
    filtered_data = [q for q in filtered_data if q["category"] == selected_category]

if query:
    filtered_data = [q for q in filtered_data if query in q["question"] or query in q["answer"]]

# 顯示結果
if not filtered_data:
    st.warning("查無相關問答，請嘗試其他關鍵字")
else:
    for item in filtered_data:
        with st.expander(f"❓ {item['question']}"):
            st.markdown(f"**分類：** `{item['category']}`")
            st.write(item["answer"])
