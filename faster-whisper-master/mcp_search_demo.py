"""
MCP Brave Search 金融資訊搜尋範例

安裝依賴：
  pip install mcp httpx

使用方式：
  1. 先到 brave.com/search/api/ 取得 API Key
  2. 設定環境變數：set BRAVE_API_KEY=你的Key
  3. 執行：python mcp_search_demo.py
"""

import asyncio
import os
import json
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


BRAVE_API_KEY = os.getenv("BRAVE_API_KEY", "YOUR_API_KEY_HERE")

# === 方法一：直接用 Brave API（最簡單） ===

async def search_with_brave_api(query: str, count: int = 5) -> list[dict]:
    """直接呼叫 Brave Search API"""
    import httpx

    url = "https://api.search.brave.com/res/v1/web/search"
    headers = {
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "X-Subscription-Token": BRAVE_API_KEY,
    }
    params = {"q": query, "count": count}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers, params=params)
        data = resp.json()

    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "description": item.get("description", ""),
        })
    return results


# === 方法二：透過 MCP Client 呼叫 Brave Search MCP Server ===

async def search_with_mcp(query: str, count: int = 5) -> list[dict]:
    """透過 MCP 協定呼叫 Brave Search MCP Server"""
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@brave/brave-search-mcp-server"],
        env={"BRAVE_API_KEY": BRAVE_API_KEY},
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            # 初始化連線
            await session.initialize()

            # 列出可用工具
            tools = await session.list_tools()
            print(f"可用工具：{[t.name for t in tools.tools]}")

            # 呼叫搜尋工具
            result = await session.call_tool(
                "brave_web_search",
                arguments={"query": query, "count": count},
            )

            # 解析結果
            output = []
            for content in result.content:
                if hasattr(content, "text"):
                    data = json.loads(content.text)
                    for item in data.get("web", {}).get("results", []):
                        output.append({
                            "title": item.get("title", ""),
                            "url": item.get("url", ""),
                            "description": item.get("description", ""),
                        })
            return output


# === 金融資訊搜尋整合 ===

async def fetch_financial_news():
    """自動搜尋多個金融主題"""
    topics = [
        "台股 今日 大盤 漲跌",
        "美股 S&P500 Nasdaq 今日",
        "台灣央行 利率 政策",
        "台積電 法說會 最新",
    ]

    print("=" * 60)
    print("  MCP 金融資訊自動搜尋")
    print("=" * 60)

    for topic in topics:
        print(f"\n搜尋：{topic}")
        print("-" * 40)

        results = await search_with_brave_api(topic, count=3)

        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['title']}")
            print(f"     {r['url']}")
            print(f"     {r['description'][:100]}...")
            print()


# === 主程式 ===

async def main():
    if BRAVE_API_KEY == "YOUR_API_KEY_HERE":
        print("[ERROR] 請設定 BRAVE_API_KEY 環境變數")
        print("  取得方式：https://brave.com/search/api/")
        print("  設定方式：set BRAVE_API_KEY=你的API_KEY")
        return

    # 範例一：直接搜尋
    print("=== 直接 Brave API 搜尋 ===\n")
    results = await search_with_brave_api("台股今日行情", count=3)
    for r in results:
        print(f"  - {r['title']}")
        print(f"    {r['url']}\n")

    # 範例二：透過 MCP 搜尋
    print("\n=== MCP 搜尋 ===\n")
    try:
        mcp_results = await search_with_mcp("台股今日行情", count=3)
        for r in mcp_results:
            print(f"  - {r['title']}")
            print(f"    {r['url']}\n")
    except Exception as e:
        print(f"  MCP 搜尋失敗：{e}")
        print("  (需要安裝 Node.js 且 npx 可用)")

    # 範例三：金融資訊自動搜尋
    print("\n=== 金融資訊自動搜尋 ===")
    await fetch_financial_news()


if __name__ == "__main__":
    asyncio.run(main())
