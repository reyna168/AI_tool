import streamlit as st
import requests

def call_nl_sql_api(query_text: str):
    """
    Calls the /nl_sql API endpoint with a natural language query.
    """
    url = "http://localhost:8000/nl_sql"  # 改成你的 MCP API URL
    headers = {"Content-Type": "application/json"}
    data = {"query": query_text}
    
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error calling API: {e}")
        return None

# Streamlit UI
st.set_page_config(page_title="NL → SQL 查詢工具", layout="wide")
st.title("🔍 自然語言 SQL 查詢介面 (MCP Client)")

query_string = st.text_area(
    "輸入查詢內容（自然語言）",
    value="請列出 2025-08-05 當天的會議標題與時間與描述，最多 10 筆",
    height=100
)

if st.button("查詢"):
    with st.spinner("正在查詢 MCP Server..."):
        result = call_nl_sql_api(query_string)

    if result:
        # 顯示原始 JSON 回應（除錯用）
        with st.expander("📦 原始 JSON 回應"):
            st.json(result)

        # SQL
        st.subheader("📜 生成的 SQL")
        st.code(result.get("sql", ""), language="sql")

        # 查詢結果
        st.subheader("📊 查詢結果")
        rows = result.get("rows", [])
        if rows:
            st.dataframe(rows)
        else:
            st.warning("查無資料")

        # 總結
        st.subheader("📝 總結回答")
        st.write(result.get("answer", "（沒有摘要）"))
