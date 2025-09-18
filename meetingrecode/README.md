

## 執行fastapi mcp 與mysql連結，提供gemini查詢資料庫

uvicorn mcp_mysql_geminiv2:app --host 0.0.0.0 --port 8080

## 執行一問一答程式 

streamlit run mcp_requestv2.py