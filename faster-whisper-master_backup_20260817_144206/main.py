"""RAG 文件問答系統 - 入口檔案"""

import argparse
import sys

from rag.cli import run_cli


def main():
    parser = argparse.ArgumentParser(
        description="RAG 文件問答系統",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用範例:
  python main.py                    啟動 CLI 互動模式 (OpenAI)
  python main.py --provider ollama  使用 Ollama 本地模型
  python main.py --ingest ./docs    載入目錄建立索引
  python main.py --ask "什麼是RAG"  直接提問
        """,
    )
    parser.add_argument(
        "--provider",
        choices=["openai", "ollama"],
        default="openai",
        help="LLM 供應商 (預設: openai)",
    )
    parser.add_argument("--ingest", type=str, help="載入文件或目錄建立索引")
    parser.add_argument("--ask", type=str, help="直接提問")
    parser.add_argument("--stream", action="store_true", help="串流模式回答")
    parser.add_argument("--reset", action="store_true", help="清空所有索引")

    args = parser.parse_args()

    # 非互動模式
    if args.ingest:
        from rag.config import RAGConfig
        from rag.rag_engine import RAGEngine

        config = RAGConfig(llm_provider=args.provider)
        errors = config.validate()
        if errors:
            for e in errors:
                print(f"[ERROR] {e}")
            sys.exit(1)

        engine = RAGEngine(config)
        from pathlib import Path

        path = Path(args.ingest)
        if path.is_dir():
            count = engine.ingest_directory(path)
        else:
            count = engine.ingest_file(path)
        print(f"成功建立 {count} 個文字區塊索引")
        return

    if args.ask:
        from rag.config import RAGConfig
        from rag.rag_engine import RAGEngine

        config = RAGConfig(llm_provider=args.provider)
        errors = config.validate()
        if errors:
            for e in errors:
                print(f"[ERROR] {e}")
            sys.exit(1)

        engine = RAGEngine(config)

        if args.stream:
            for chunk in engine.query(args.ask, stream=True):
                print(chunk, end="", flush=True)
            print()
        else:
            answer = engine.query(args.ask)
            print(answer)
        return

    if args.reset:
        from rag.config import RAGConfig
        from rag.rag_engine import RAGEngine

        config = RAGConfig(llm_provider=args.provider)
        engine = RAGEngine(config)
        engine.reset()
        print("已清空所有索引")
        return

    # 互動模式
    run_cli(llm_provider=args.provider)


if __name__ == "__main__":
    main()
