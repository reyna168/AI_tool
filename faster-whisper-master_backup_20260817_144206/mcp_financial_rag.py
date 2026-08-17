"""
MCP 金融 RAG 系統
結合 Brave Search MCP + ChromaDB + LLM 即時金融資訊問答

安裝：
  pip install httpx chromadb openai
"""

import asyncio
import json
import os
from dataclasses import dataclass
from datetime import datetime

import httpx
import chromadb
from openai import OpenAI


# === 設定 ===

@dataclass
class Config:
    brave_api_key: str = os.getenv("BRAVE_API_KEY", "")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_model: str = "gpt-4o-mini"


# === Brave Search MCP Client ===

class BraveSearchClient:
    """Brave Search API 封裝（等同 MCP brave_web_search 工具）"""

    BASE_URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "X-Subscription-Token": api_key,
        }

    async def search(self, query: str, count: int = 5) -> list[dict]:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                self.BASE_URL,
                headers=self.headers,
                params={"q": query, "count": count, "search_lang": "zh-hant"},
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("web", {}).get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("description", ""),
                "age": item.get("age", ""),
            })
        return results

    async def search_financial(self, keywords: list[str]) -> list[dict]:
        """多關鍵字金融搜尋"""
        all_results = []
        for kw in keywords:
            try:
                results = await self.search(kw, count=3)
                all_results.extend(results)
            except Exception as e:
                print(f"  [WARN] 搜尋 '{kw}' 失敗: {e}")
        return all_results


# === 向量資料庫 ===

class NewsVectorDB:
    """金融新聞向量資料庫"""

    def __init__(self):
        self.client = chromadb.Client()
        self.collection = self.client.get_or_create_collection(
            name="financial_news",
            metadata={"hnsw:space": "cosine"},
        )

    def add_news(self, articles: list[dict]):
        """加入新聞到向量庫"""
        if not articles:
            return

        ids = [f"news_{i}_{datetime.now().timestamp()}" for i in range(len(articles))]
        documents = [
            f"{a['title']}\n{a['snippet']}" for a in articles
        ]
        metadatas = [
            {"title": a["title"], "url": a["url"], "age": a.get("age", "")}
            for a in articles
        ]

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    def query(self, question: str, top_k: int = 5) -> list[dict]:
        """查詢相關新聞"""
        results = self.collection.query(
            query_texts=[question],
            n_results=top_k,
        )

        output = []
        for i in range(len(results["documents"][0])):
            output.append({
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results["distances"] else None,
            })
        return output

    def count(self) -> int:
        return self.collection.count()


# === LLM 問答 ===

class FinancialQA:
    """金融問答引擎"""

    SYSTEM_PROMPT = """你是專業的金融分析師。根據提供的即時新聞資料回答問題。

規則：
1. 只根據提供的新聞資料回答
2. 引用新聞來源（標題和網址）
3. 如果資料不足，明確告知
4. 使用繁體中文"""

    def __init__(self, config: Config):
        self.client = OpenAI(api_key=config.openai_api_key)
        self.model = config.openai_model

    def answer(self, question: str, news_context: str) -> str:
        user_prompt = f"""## 即時金融新聞

{news_context}

---

## 問題

{question}

請根據上方新聞資料回答。"""

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
        return response.choices[0].message.content


# === 主系統 ===

class MCPFinancialRAG:
    """MCP 金融 RAG 系統"""

    # 金融搜尋關鍵字模板
    SEARCH_TOPICS = [
        "{market}股 今日 行情 大盤",
        "{market}股 漲跌 三大法人",
        "台積電 最新消息",
        "美股 S&P500 Nasdaq 今日",
        "聯準會 利率 政策",
    ]

    def __init__(self, config: Config | None = None):
        self.config = config or Config()
        self.search_client = BraveSearchClient(self.config.brave_api_key)
        self.vector_db = NewsVectorDB()
        self.qa = FinancialQA(self.config)

    async def update_news(self, market: str = "台"):
        """從網路抓取最新金融新聞並建立索引"""
        print(f"正在搜尋 {market} 股金融新聞...")

        keywords = [t.format(market=market) for t in self.SEARCH_TOPICS]
        articles = await self.search_client.search_financial(keywords)

        # 去重
        seen = set()
        unique = []
        for a in articles:
            if a["url"] not in seen:
                seen.add(a["url"])
                unique.append(a)

        self.vector_db.add_news(unique)
        print(f"已索引 {len(unique)} 則新聞（共 {self.vector_db.count()} 則）")
        return unique

    def ask(self, question: str) -> str:
        """提問"""
        results = self.vector_db.query(question)

        if not results:
            return "目前沒有相關金融新聞資料，請先執行 update_news() 更新。"

        # 組裝上下文
        context_parts = []
        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            context_parts.append(
                f"### 新聞 {i}\n"
                f"標題: {meta['title']}\n"
                f"來源: {meta['url']}\n"
                f"時間: {meta.get('age', 'N/A')}\n"
                f"內容: {r['content']}"
            )
        context = "\n\n".join(context_parts)

        return self.qa.answer(question, context)


# === CLI ===

async def main():
    config = Config()

    if not config.brave_api_key:
        print("[ERROR] 請設定 BRAVE_API_KEY")
        print("  set BRAVE_API_KEY=你的API_KEY")
        return

    if not config.openai_api_key:
        print("[ERROR] 請設定 OPENAI_API_KEY")
        return

    rag = MCPFinancialRAG(config)

    # 第一步：抓取新聞
    await rag.update_news("台")

    # 第二步：互動問答
    print("\n" + "=" * 50)
    print("  金融 RAG 問答系統（Ctrl+C 離開）")
    print("=" * 50)

    while True:
        try:
            question = input("\n金融問題 > ").strip()
            if not question:
                continue

            # 先更新新聞再回答
            if question in ("update", "更新", "refresh"):
                await rag.update_news("台")
                continue

            answer = rag.ask(question)
            print(f"\n{answer}")

        except (KeyboardInterrupt, EOFError):
            print("\n再見！")
            break


if __name__ == "__main__":
    asyncio.run(main())
