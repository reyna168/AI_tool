# file: mcp_mysql_gemini.py
import os
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

# 載入 .env
load_dotenv()
DB_URL = os.getenv("DB_URL", "mysql+pymysql://root:""@localhost:3306/yilsystem")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")  # Gemini API Key

# MySQL engine
engine = create_engine(DB_URL, pool_pre_ping=True)

# Gemini LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GEMINI_API_KEY, temperature=0)

app = FastAPI()

# 資料模型
class NLQuery(BaseModel):
    query: str

# SQL 安全檢查
def safe_sql(sql: str) -> bool:
    sql_low = sql.lower()
    forbidden = ["insert", "update", "delete", "drop", "alter", ";"]
    if not sql_low.strip().startswith("select"):
        return False
    for f in forbidden:
        if f in sql_low:
            return False
    return True

# 使用 Gemini 生成 SQL
def generate_sql(nl: str) -> str:
    prompt = f"""
你是 MySQL 查詢助手。請輸出純 SQL 語句，不要有任何解釋或附加文字，不要加分號。
需求：{nl}
限制：
- 只能使用 SELECT
- 必須加上 LIMIT 50
- 不允許修改資料
只輸出 SQL，不要多餘解釋。
"""
    sql_code = llm.invoke(prompt).content.strip()
    sql_code = sql_code.strip().strip("```sql").strip("```").strip(";")  # 清理多餘格式
    return sql_code

# 使用 Gemini 生成最終中文回答
def summarize_answer(question: str, rows: List[Dict]) -> str:
    prompt = f"""
使用者問題：
{question}

SQL 查詢結果(JSON)：
{rows}

請用中文簡短總結並回答使用者，保留關鍵數字與資訊。
"""
    return llm.invoke(prompt).content.strip()

@app.post("/nl_sql")
def nl_to_sql(q: NLQuery):
    sql = generate_sql(q.query)
    print(f"DEBUG: Generated SQL = {sql}")  # 先看 Gemini 生什麼
    if not safe_sql(sql):
        raise HTTPException(status_code=400, detail="生成的 SQL 不安全")
    
    with engine.connect() as conn:
        result = conn.execute(text(sql))
        rows = [dict(r) for r in result.fetchall()]
    
    answer = summarize_answer(q.query, rows)
    return {"sql": sql, "rows": rows, "answer": answer}
