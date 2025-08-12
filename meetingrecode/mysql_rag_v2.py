# file: sql_llm_query.py
# 需求: pip install pymysql sqlalchemy langchain langchain-google-genai python-dotenv

import os
import re
import pymysql
from sqlalchemy import create_engine, text
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.utilities import SQLDatabase
from langchain.chains import create_sql_query_chain
from dotenv import load_dotenv

load_dotenv()

# --- Config ---
DB_USER = "root"
DB_PASS = ""  # 資料庫密碼
DB_HOST = "127.0.0.1"
DB_PORT = 3306
DB_NAME = "yilsystem"

GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")

# 1. 建立 SQLAlchemy engine
db_connection_str = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
engine = create_engine(db_connection_str)

# 2. 建立 SQLDatabase wrapper
db = SQLDatabase(engine)

# 3. 初始化 Google Gemini LLM
llm = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=GOOGLE_API_KEY,
    temperature=0
)

# 4. 建立 SQL 查詢鏈
query_chain = create_sql_query_chain(llm, db)

# 5. 定義自然語言問題
question = "請列出 2025-08-05 當天的會議標題與時間與描述，最多 10 筆。"

# 6. 先讓 LLM 產生 SQL
sql_query = query_chain.invoke({"question": question})

# --- 清理多餘的 Markdown 標籤與空白 ---
sql_query_clean = re.sub(r"```[\s\S]*?```", lambda m: m.group(0).replace("```mysql", "").replace("```", ""), sql_query)
sql_query_clean = sql_query_clean.strip()

print("\n--- 生成的 SQL ---")
print(sql_query_clean)

# 7. 執行 SQL 並輸出結果
try:
    with engine.connect() as conn:
        result = conn.execute(text(sql_query_clean))
        rows = result.fetchall()
        print("\n--- 查詢結果 ---")
        for row in rows:
            print(row)
except Exception as e:
    print(f"\n執行 SQL 發生錯誤: {e}")
