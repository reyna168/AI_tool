"""RAG 系統配置管理"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


@dataclass
class RAGConfig:
    """RAG 系統配置"""

    # === LLM 設定 ===
    # "openai" 或 "ollama"
    llm_provider: str = "openai"
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = "gpt-4o-mini"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    temperature: float = 0.3
    max_tokens: int = 2048

    # === Embedding 設定 ===
    # "openai" 或 "local"
    embedding_provider: str = "openai"
    openai_embedding_model: str = "text-embedding-3-small"
    local_embedding_model: str = "all-MiniLM-L6-v2"

    # === ChromaDB 設定 ===
    persist_directory: str = "chroma_db"
    collection_name: str = "documents"

    # === 文件分割設定 ===
    chunk_size: int = 500
    chunk_overlap: int = 100
    supported_extensions: list[str] = field(
        default_factory=lambda: [".txt", ".md", ".pdf", ".csv", ".json", ".py", ".docx"]
    )

    # === RAG 檢索設定 ===
    top_k: int = 5

    @property
    def chroma_path(self) -> Path:
        return Path(self.persist_directory)

    def validate(self) -> list[str]:
        errors = []
        if self.llm_provider == "openai" and not self.openai_api_key:
            errors.append("使用 OpenAI 時需要設定 OPENAI_API_KEY")
        if self.embedding_provider == "openai" and not self.openai_api_key:
            errors.append("使用 OpenAI embedding 時需要設定 OPENAI_API_KEY")
        return errors
