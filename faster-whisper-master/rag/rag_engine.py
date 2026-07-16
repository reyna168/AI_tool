"""RAG 核心引擎 - 整合文件載入、向量檢索與 LLM 生成"""

from pathlib import Path

from rag.config import RAGConfig
from rag.document_loader import Document, load_directory, load_document
from rag.llm import LLMClient
from rag.text_splitter import TextChunk, split_documents
from rag.vector_store import VectorStore


SYSTEM_PROMPT = """你是一個專業的問答助手。你會根據提供的參考資料來回答使用者的問題。

規則：
1. 只根據提供的參考資料回答，不要編造資訊
2. 如果參考資料中沒有相關資訊，請明確告知使用者
3. 回答時請引用來源（檔案名稱）
4. 使用繁體中文回答"""

RAG_PROMPT_TEMPLATE = """## 參考資料

{context}

---

## 使用者問題

{question}

請根據上方參考資料回答問題。"""


class RAGEngine:
    """RAG 引擎"""

    def __init__(self, config: RAGConfig | None = None):
        self.config = config or RAGConfig()

        errors = self.config.validate()
        if errors:
            raise ValueError("配置錯誤:\n" + "\n".join(f"  - {e}" for e in errors))

        self.vector_store = VectorStore(self.config)
        self.llm = LLMClient(self.config)

    def ingest_file(self, file_path: str | Path) -> int:
        """載入單一文件並建立索引"""
        doc = load_document(file_path)
        chunks = split_documents(
            [doc],
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        count = self.vector_store.add_chunks(chunks)
        return count

    def ingest_directory(self, dir_path: str | Path) -> int:
        """載入目錄下所有文件並建立索引"""
        docs = load_directory(dir_path, self.config.supported_extensions)
        if not docs:
            return 0
        chunks = split_documents(
            docs,
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
        )
        count = self.vector_store.add_chunks(chunks)
        return count

    def retrieve(self, query: str, top_k: int | None = None) -> list[dict]:
        """檢索相關文件區塊"""
        k = top_k or self.config.top_k
        return self.vector_store.query(query, top_k=k)

    def _build_context(self, results: list[dict]) -> str:
        """組裝檢索結果為上下文"""
        parts = []
        for i, r in enumerate(results, 1):
            source = r["metadata"].get("source", "unknown")
            parts.append(f"### 參考資料 {i}（來源: {source}）\n{r['content']}")
        return "\n\n".join(parts)

    def query(self, question: str, top_k: int | None = None, stream: bool = False) -> str:
        """問答：檢索 + 生成"""
        results = self.retrieve(question, top_k)
        context = self._build_context(results)

        user_prompt = RAG_PROMPT_TEMPLATE.format(context=context, question=question)

        if stream:
            return self.llm.stream_chat(SYSTEM_PROMPT, user_prompt)
        return self.llm.chat(SYSTEM_PROMPT, user_prompt)

    def get_stats(self) -> dict:
        """取得系統狀態"""
        return {
            "llm_provider": self.config.llm_provider,
            "llm_model": (
                self.config.openai_model
                if self.config.llm_provider == "openai"
                else self.config.ollama_model
            ),
            "embedding_provider": self.config.embedding_provider,
            "total_chunks": self.vector_store.count(),
        }

    def reset(self):
        """清空向量資料庫"""
        self.vector_store.reset()
