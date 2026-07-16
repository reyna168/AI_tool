"""文字分割器 - 將文件切分為適合 embedding 的小塊"""

from dataclasses import dataclass

from rag.document_loader import Document


@dataclass
class TextChunk:
    """文字區塊"""

    content: str
    metadata: dict

    def __repr__(self):
        return f"TextChunk(length={len(self.content)})"


def split_text(
    text: str,
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[str]:
    """使用遞迴字元分割法切分文字"""
    separators = ["\n\n", "\n", "。", ".", "！", "!", "？", "?", "；", ";", " "]
    return _recursive_split(text, separators, chunk_size, chunk_overlap)


def _recursive_split(
    text: str,
    separators: list[str],
    chunk_size: int,
    chunk_overlap: int,
) -> list[str]:
    """遞迴分割文字"""
    if len(text) <= chunk_size:
        return [text.strip()] if text.strip() else []

    separator = separators[0] if separators else ""
    remaining_separators = separators[1:] if len(separators) > 1 else []

    if separator:
        parts = text.split(separator)
    else:
        # 沒有分隔符時，直接按長度切
        parts = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]

    chunks = []
    current = ""

    for part in parts:
        candidate = current + separator + part if current else part
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current.strip():
                chunks.append(current.strip())
            current = part

    if current.strip():
        chunks.append(current.strip())

    # 處理重疊
    if chunk_overlap > 0 and len(chunks) > 1:
        overlapped = [chunks[0]]
        for i in range(1, len(chunks)):
            prev_tail = chunks[i - 1][-chunk_overlap:]
            overlapped.append(prev_tail + " " + chunks[i])
        chunks = overlapped

    return chunks


def split_documents(
    documents: list[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 100,
) -> list[TextChunk]:
    """將文件列表切分為 TextChunk 列表"""
    all_chunks = []

    for doc in documents:
        text_chunks = split_text(doc.content, chunk_size, chunk_overlap)
        for i, chunk_text in enumerate(text_chunks):
            metadata = {**doc.metadata, "chunk_index": i}
            all_chunks.append(TextChunk(content=chunk_text, metadata=metadata))

    return all_chunks
