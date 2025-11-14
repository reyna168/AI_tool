# YWC 科技筆記 - 完整文章索引

**網站:** https://ywctech.net/  
**簡介:** 愛好ML/AI的中年軟體工程師

---

## 📝 最新文章

### 2025年

1. **Agile is also Context Engineering - 敏捷開發的 Demo, CI/CD, 儀式等等**
   - 日期: July 11, 2025
   
2. **用 Playwright MCP 跟 Claude 做 AI 爬蟲,幫你操作網頁**
   - 日期: April 26, 2025
   - 連結: https://ywctech.net/ml-ai/playwright-mcp-crawler/
   - 簡介: 用 Playwright MCP 跟 Claude Desktop 或其他的 MCP client, 你只要跟 AI 講人話,他就會幫你瀏覽網站、操作、整理資料!

3. **AI 寫程式 與 Vibe Coding 雜感**
   - 日期: March 23, 2025

4. **STORM / CO-STORM 多角色合作,給你長文跟思路**
   - 日期: January 5, 2025
   - 連結: https://ywctech.net/ml-ai/storm-co-storm-generate-articles/
   - 簡介: STORM 與 CO-STORM 是史丹佛開發的多智慧代理人系統,專為長文生成與思維輔助設計。透過多角度提問與網路檢索,它能產生結構清晰的文章、心智圖及思考過程,甚至允許用戶參與對話

---

## 🤖 Machine Learning / AI 系列

### RAG (Retrieval-Augmented Generation) 相關

5. **進階 RAG 技巧 - 到底 RAG 是什麼?**
   - 日期: November 29, 2024
   - 連結: https://ywctech.net/ml-ai/beyond-naive-rag-summary-intro/
   - 簡介: RAG 雖然概念是搜尋後生成,但萬一效果不好怎麼辦?這系列文整理了一些文獻,讓你的 RAG 不僅僅是 Embedding + Vector DB + LLM

6. **進階 RAG 技巧 - 改變使用者問題 Transform Query**
   - 日期: November 30, 2024
   - 連結: https://ywctech.net/ml-ai/beyond-naive-rag-query-transformation/
   - 簡介: 要怎麼改變使用者的問題來提升 RAG 生成的效果?本文介紹多種策略,包括 HyDE、Self-querying Retrieval、Step-back Prompting、Least-to-most Prompting 以及 RAG Fusion

7. **RAG 跟傳統搜尋不一樣的地方**
   - 日期: June 29, 2024
   - 連結: https://ywctech.net/ml-ai/difference-between-search-and-rag/
   - 簡介: 有人說 RAG 就是用了 vector database -- 錯,這不一定。讓我告訴你傳統搜尋 (search) 跟檢索增強生成 (RAG) 不同的兩個點

### LangChain 與 LlamaIndex 比較系列

8. **LangChain 與 LlamaIndex 比較 - Naive RAG**
   - 日期: May 27, 2024
   - 連結: https://ywctech.net/ml-ai/langchain-vs-llamaindex-naive-rag/
   - 簡介: LangChain vs. LlamaIndex,從 RAG 的問答引擎為例子來探討兩者的異同、特性。這是一系列的比較,讓你更了解該選擇 LangChain 還是 LlamaIndex

9. **LangChain 與 LlamaIndex 比較 - RAG 多輪對話**
   - 日期: May 29, 2024
   - 連結: https://ywctech.net/ml-ai/langchain-vs-llamaindex-rag-chat/

### LlamaIndex 系列

10. **LlamaIndex 學習筆記 - Streamlit 做 RAG chatbot UI**
    - 日期: April 24, 2024
    - 連結: https://ywctech.net/ml-ai/llamaindex-adhoc-note-streamlit-ui/
    - 簡介: LlamaIndex 做好 RAG 的函數/API 後,利用 Streamlit 做出漂亮介面,讓我們能跟 ChatGPT 一樣真的打字對話!

### LangGraph 與 Agent 系列

11. **LangGraph: LangChain Agent 的殺手鐧 (進階)**
    - 日期: June 12, 2024
    - 連結: https://ywctech.net/ml-ai/langchain-langgraph-agent-part2/
    - 簡介: LangGraph 是 LangChain 生態系 v0.2 主打的框架,也是實作 Agent 代理人的建議。這篇文章是進階的部分,LangGraph 的特點:State 更新、Human-in-the-loop 等等

12. **用 LangGraph 寫 LeetCode 解題機器人 Agent**
    - 日期: June 19, 2024
    - 連結: https://ywctech.net/ml-ai/write-leetcode-agent-in-langgraph/
    - 簡介: LangGraph 是 LangChain 生態系 v0.2 主打的框架,也是實作 Agent 代理人的建議。我用解 LeetCode 真實的案例,介紹用 LangGraph 寫 agent 是什麼樣子

### 資訊檢索 (Information Retrieval) 基礎

13. **白話圖解 - 什麼是 TF-IDF**
    - 日期: July 13, 2024
    - 連結: https://ywctech.net/ml-ai/what-is-tfidf/
    - 簡介: 當搜尋某個關鍵字,TF-IDF 可用來預測在眾多文章中,哪一篇最相關。TFIDF 是資訊檢索 (IR) 經典的統計方法,非常重要,但了解 TF 跟 IDF 一點也不難

14. **白話圖解 - 什麼是 BM25**
    - 日期: July 16, 2024
    - 連結: https://ywctech.net/ml-ai/what-is-bm25/
    - 簡介: 搜尋引擎如 Elasticsearch 常用 Okapi BM25 預測文章跟關鍵字的相關度。BM25 有細膩的數學公式,我用白話文跟圖表慢慢解釋,讓你一目瞭然

15. **白話文告訴你 - 什麼是 Embedding**
    - 日期: January 18, 2024
    - 連結: https://ywctech.net/ml-ai/what-is-embedding/
    - 簡介: 在 AI 常聽到 Embedding,但到底是什麼?淺顯易懂的解釋:跟學生小團體以及新創夥伴一樣!這是什麼意思呢?

### Embedding 與模型服務

16. **本機架設自己的 embedding 服務**
    - 日期: August 1, 2024
    - 連結: https://ywctech.net/ml-ai/how-to-serve-embedding/
    - 簡介: 以 mxbai-embed-large 為例,教你怎麼用別人的 embedding model 架設成服務,讓你的應用程式可以去呼叫。Embedding 不是只有 OpenAI 才行!

### LLM 評估與研究

17. **LLM as a Judge: 用語言模型來評估好壞**
    - 日期: August 24, 2024
    - 連結: https://ywctech.net/ml-ai/paper-llm-as-a-judge/
    - 簡介: 用 LLM 當裁判,例如評估一個問題的答案好壞,或許比人類快又便宜,但用 AI 判斷真的準確嗎?要小心各種偏見!這篇論文列出一些常見問題與解法

### 推薦系統

18. **如果我是 Threads 工程師,要怎麼寫推薦演算法**
    - 日期: June 18, 2024
    - 連結: https://ywctech.net/ml-ai/how-would-i-write-threads-recommendation/
    - 簡介: 你逛電商或社交平台,那些推薦給你的文章產品是怎麼來的?Embedding? Matrix Factorization? Cold Start? 吸引呈現個人化有趣的東西,這邊列出一些可能的方式

### AI Coding

19. **從 Vibe Coding 到 AI Coding**
    - 日期: September 28, 2025
    - 連結: https://ywctech.net/ml-ai/sharing-from-vibe-coding-to-ai-coding/
    - 簡介: 如果想寫程式但沒經驗,這教你踏出第一步的心法。如果會寫程式但只會跟 ChatGPT 交談,這教你目前 AI coding 趨勢,包括 context engineering 跟 agentic coding 等等

---

## 📰 新聞與評測

20. **Claude 新模型 3.5 Sonnet 真的好嗎?實測**
    - 日期: June 27, 2024
    - 連結: https://ywctech.net/ml-ai/claude-3.5-sonnet-new-model/
    - 簡介: 最近 Claude 推出了新版本 3.5 的 Sonnet 模型,以及新功能 Artifact 讓你即時預覽他產生的網頁,甚至互動!以下放了幾個實測案例

21. **[新聞] Ollama v0.2 釋出 - 並行運作更實用**
    - 日期: July 10, 2024

22. **[新聞] Google 公布 Gemini 1.5 -- 多型態的生成模型**
    - 日期: February 16, 2024

23. **[新聞] OpenAI 公布 Sora -- 文字生成影片**
    - 日期: February 15, 2024

---

## 💻 Tech Stuff 技術文章

24. **Virtual environments of JupyterLab, kernels, and dependencies**
    - 日期: February 5, 2024
    - 連結: https://ywctech.net/tech/jupyterlab-ipykernel-venv/
    - 簡介: How to make an isolated ML development environments in JupyterLab with ipykernel, so you can use different versions of libraries and pythons

---

## 📚 主要標籤分類

- **RAG** - 檢索增強生成相關文章
- **LangChain** - LangChain 框架相關
- **LlamaIndex** - LlamaIndex 框架相關
- **Embedding** - 向量嵌入相關
- **資訊檢索 (Information Retrieval)** - TF-IDF, BM25 等
- **LLM** - 大型語言模型
- **Agent** - 智慧代理人
- **新聞** - AI/ML 領域新聞
- **技術** - 軟體工程相關技術

---

## 🔍 網站特色

1. **深入淺出的教學風格** - 使用白話文和圖解說明複雜的 AI/ML 概念
2. **實戰導向** - 包含大量實際程式碼範例和實作筆記
3. **框架比較** - 詳細比較 LangChain 與 LlamaIndex 等主流框架
4. **RAG 專題** - 系統性介紹 RAG 技術,從基礎到進階
5. **中文技術內容** - 提供高品質的中文 AI/ML 技術文章

---

**網站作者:** YWC - 愛好 ML/AI 的中年軟體工程師  
**建構工具:** Hugo & Congo 主題

*最後更新: 2025年11月*
