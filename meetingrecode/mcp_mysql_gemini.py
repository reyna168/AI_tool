import os
import re
from typing import List, Dict
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy import create_engine, text, inspect
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain

# 載入 .env
load_dotenv()
DB_URL = os.getenv("DB_URL", "mysql+pymysql://root:""@localhost:3306/yilsystem")
GEMINI_API_KEY = os.getenv("GOOGLE_API_KEY")

# MySQL engine
engine = create_engine(DB_URL, pool_pre_ping=True)

# 測試資料庫連線
try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("資料庫連線成功")
except Exception as e:
    print(f"資料庫連線失敗: {e}")
    raise

# Gemini LLM
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=GEMINI_API_KEY, temperature=0)

app = FastAPI()

# 資料模型
class NLQuery(BaseModel):
    query: str

# 取得資料庫結構並傳給 LLM
def get_schema_info():
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    schema = {}
    for table_name in tables:
        columns = [col['name'] for col in inspector.get_columns(table_name)]
        schema[table_name] = columns
    return schema

# 使用 LangChain 和 Gemini 生成 SQL
def generate_sql_with_langchain(nl: str) -> str:
    db = SQLDatabase(engine)
    query_chain = create_sql_query_chain(llm, db)
    sql_query = query_chain.invoke({"question": nl})
    
    # 清理多餘的 Markdown 標籤與空白
    sql_query_clean = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).replace("```mysql", "").replace("```", ""), sql_query)
    sql_query_clean = sql_query_clean.strip()
    
    # 強制加上 LIMIT 50，以符合您的需求
    if "limit" not in sql_query_clean.lower():
        sql_query_clean += " LIMIT 50"
    
    return sql_query_clean


# SQL 安全檢查
def safe_sql(sql: str) -> bool:
    sql_low = sql.lower().strip()
    forbidden = ["insert ", "update ", "delete ", "drop ", "alter "]
    if not sql_low.startswith("select "):
        return False
    for f in forbidden:
        if f in sql_low:
            return False
    return True

# 使用 Gemini 生成最終中文回答
def summarize_answer(question: str, rows: List[Dict]) -> str:
    prompt = f"""
使用者問題：
{question}

SQL 查詢結果(JSON，僅前 5 筆)：
{rows[:5]}

請用中文簡短總結並回答使用者，保留關鍵數字與資訊。
"""
    return llm.invoke(prompt).content.strip()

@app.post("/nl_sql")
def nl_to_sql(q: NLQuery):
    print(f"使用者輸入: {q.query}")
    
    # 使用 LangChain 產生 SQL
    sql = generate_sql_with_langchain(q.query)
    print(f"DEBUG: Generated SQL = {sql}")
    
    if not safe_sql(sql):
        raise HTTPException(status_code=400, detail="生成的 SQL 不安全")
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = [dict(r._mapping) for r in result.fetchall()]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"SQL 執行失敗: {str(e)}")
    
    answer = summarize_answer(q.query, rows)
    return {"sql": sql, "rows": rows, "answer": answer}