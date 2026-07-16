"""CLI 互動介面"""

import sys
from pathlib import Path

from rag.config import RAGConfig
from rag.rag_engine import RAGEngine


HELP_TEXT = """
╔══════════════════════════════════════════╗
║        RAG 文件問答系統                  ║
╚══════════════════════════════════════════╝

指令:
  ingest <路徑>     載入文件或目錄建立索引
  ask <問題>        根據已索引文件提問
  stream <問題>     串流模式提問（即時顯示回答）
  stats             顯示系統狀態
  reset             清空所有索引資料
  help              顯示此說明
  quit / exit       離開程式
"""


def print_colored(text: str, color: str = "white"):
    colors = {
        "green": "\033[92m",
        "yellow": "\033[93m",
        "cyan": "\033[96m",
        "red": "\033[91m",
        "white": "\033[0m",
        "bold": "\033[1m",
    }
    reset = "\033[0m"
    print(f"{colors.get(color, '')}{text}{reset}")


def handle_ingest(engine: RAGEngine, path_str: str):
    path = Path(path_str.strip())
    if not path.exists():
        print_colored(f"  路徑不存在: {path}", "red")
        return

    print_colored(f"  正在載入: {path} ...", "yellow")

    if path.is_dir():
        count = engine.ingest_directory(path)
    else:
        count = engine.ingest_file(path)

    print_colored(f"  成功建立 {count} 個文字區塊索引", "green")


def handle_ask(engine: RAGEngine, question: str):
    print_colored("  檢索中...", "yellow")

    results = engine.retrieve(question)
    if not results:
        print_colored("  找不到相關資料", "red")
        return

    print_colored(f"  找到 {len(results)} 筆相關資料，正在生成回答...\n", "cyan")

    answer = engine.query(question)
    print_colored("─" * 50, "white")
    print(answer)
    print_colored("─" * 50, "white")


def handle_stream(engine: RAGEngine, question: str):
    print_colored("  檢索中...", "yellow")

    results = engine.retrieve(question)
    if not results:
        print_colored("  找不到相關資料", "red")
        return

    print_colored(f"  找到 {len(results)} 筆相關資料，串流回答中...\n", "cyan")
    print_colored("─" * 50, "white")

    for chunk in engine.query(question, stream=True):
        print(chunk, end="", flush=True)

    print()  # 換行
    print_colored("─" * 50, "white")


def run_cli(llm_provider: str = "openai"):
    """啟動 CLI 互動介面"""
    config = RAGConfig(llm_provider=llm_provider)

    print_colored(HELP_TEXT, "cyan")
    print_colored(f"  LLM: {config.llm_provider}", "yellow")
    if config.llm_provider == "openai":
        print_colored(f"  Model: {config.openai_model}", "yellow")
    else:
        print_colored(f"  Model: {config.ollama_model}", "yellow")

    errors = config.validate()
    if errors:
        for e in errors:
            print_colored(f"  [ERROR] {e}", "red")
        print_colored("  請設定環境變數後重試", "red")
        return

    engine = RAGEngine(config)

    stats = engine.get_stats()
    print_colored(f"  已有索引: {stats['total_chunks']} 個區塊\n", "green")

    while True:
        try:
            user_input = input("RAG > ").strip()
        except (KeyboardInterrupt, EOFError):
            print_colored("\n再見！", "cyan")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit", "q"):
            print_colored("再見！", "cyan")
            break

        if user_input.lower() == "help":
            print_colored(HELP_TEXT, "cyan")
            continue

        if user_input.lower() == "stats":
            stats = engine.get_stats()
            print_colored(f"  LLM Provider: {stats['llm_provider']}", "white")
            print_colored(f"  LLM Model: {stats['llm_model']}", "white")
            print_colored(f"  Embedding: {stats['embedding_provider']}", "white")
            print_colored(f"  索引區塊數: {stats['total_chunks']}", "white")
            continue

        if user_input.lower() == "reset":
            confirm = input("  確定要清空所有索引？(y/N) ").strip()
            if confirm.lower() == "y":
                engine.reset()
                print_colored("  已清空索引", "green")
            continue

        parts = user_input.split(" ", 1)
        cmd = parts[0].lower()
        arg = parts[1] if len(parts) > 1 else ""

        if cmd == "ingest":
            if not arg:
                print_colored("  請指定路徑: ingest <檔案或目錄路徑>", "red")
            else:
                handle_ingest(engine, arg)
        elif cmd == "ask":
            if not arg:
                print_colored("  請輸入問題: ask <你的問題>", "red")
            else:
                handle_ask(engine, arg)
        elif cmd == "stream":
            if not arg:
                print_colored("  請輸入問題: stream <你的問題>", "red")
            else:
                handle_stream(engine, arg)
        else:
            # 預設當作 ask
            handle_ask(engine, user_input)


if __name__ == "__main__":
    provider = sys.argv[1] if len(sys.argv) > 1 else "openai"
    run_cli(llm_provider=provider)
