"""ChromaDB 向量資料庫管理"""

from pathlib import Path

import chromadb
from chromadb.config import Settings

from rag.config import RAGConfig
from rag.text_splitter import TextChunk


class VectorStore:
    """ChromaDB 向量資料庫封裝"""

    def __init__(self, config: RAGConfig):
        self.config = config
        self._embedding_fn = self._create_embedding_fn()
        self._client = self._create_client()
        self._collection = self._get_or_create_collection()

    def _create_embedding_fn(self):
        """根據配置建立 embedding 函數"""
        if self.config.embedding_provider == "openai":
            return chromadb.utils.embedding_functions.OpenAIEmbeddingFunction(
                api_key=self.config.openai_api_key,
                model_name=self.config.openai_embedding_model,
            )
        else:
            return (
                chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.config.local_embedding_model
                )
            )

    def _create_client(self) -> chromadb.ClientAPI:
        persist_dir = str(self.config.chroma_path)
        Path(persist_dir).mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=persist_dir)

    def _get_or_create_collection(self):
        return self._client.get_or_create_collection(
            name=self.config.collection_name,
            embedding_function=self._embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[TextChunk], batch_size: int = 100) -> int:
        """批量加入文字區塊"""
        total = 0
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i : i + batch_size]
            self._collection.add(
                documents=[c.content for c in batch],
                metadatas=[c.metadata for c in batch],
                ids=[f"doc_{i + j}" for j in range(len(batch))],
            )
            total += len(batch)
        return total

    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        """查詢最相關的區塊"""
        results = self._collection.query(
            query_texts=[query_text],
            n_results=top_k,
        )

        output = []
        for i in range(len(results["documents"][0])):
            output.append(
                {
                    "content": results["documents"][0][i],
                    "metadata": results["metadatas"][0][i],
                    "distance": results["distances"][0][i] if results["distances"] else None,
                }
            )
        return output

    def count(self) -> int:
        """回傳文件區塊總數"""
        return self._collection.count()

    def reset(self):
        """清空資料庫"""
        self._client.delete_collection(self.config.collection_name)
        self._collection = self._get_or_create_collection()

    def get_all_metadatas(self) -> list[dict]:
        """取得所有文件的 metadata"""
        results = self._collection.get(include=["metadatas"])
        return results["metadatas"]
