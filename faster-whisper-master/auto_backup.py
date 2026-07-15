import os
import shutil
import time
from datetime import datetime

# 來源目錄
SOURCE_DIR = r"F:\python專案\faster-whisper-master"

# 備份目標目錄
BACKUP_DIR = r"C:\Users\USER\Documents\GitHub\AI_tool\faster-whisper-master"

# 排除的目錄
EXCLUDE_DIRS = {".git", "__pycache__", ".venv", "venv", "env", ".idea", ".vscode"}

# 要備份的副檔名
BACKUP_EXTENSIONS = {".py", ".txt", ".md", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini"}

# 自動備份間隔（秒）
BACKUP_INTERVAL = 60  # 每60秒檢查一次


def backup_files():
    """備份專案檔案到目標目錄"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 開始備份...")

    if not os.path.exists(SOURCE_DIR):
        print(f"錯誤：來源目錄不存在 - {SOURCE_DIR}")
        return False

    os.makedirs(BACKUP_DIR, exist_ok=True)

    copied = 0
    skipped = 0
    errors = 0

    for root, dirs, files in os.walk(SOURCE_DIR):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for file in files:
            ext = os.path.splitext(file)[1].lower()
            if ext not in BACKUP_EXTENSIONS:
                skipped += 1
                continue

            src_path = os.path.join(root, file)
            rel_path = os.path.relpath(src_path, SOURCE_DIR)
            dst_path = os.path.join(BACKUP_DIR, rel_path)

            try:
                # 檔案是否已存在且內容相同
                if os.path.exists(dst_path):
                    src_stat = os.stat(src_path)
                    dst_stat = os.stat(dst_path)
                    if src_stat.st_size == dst_stat.st_size and \
                       src_stat.st_mtime <= dst_stat.st_mtime:
                        continue

                os.makedirs(os.path.dirname(dst_path), exist_ok=True)
                shutil.copy2(src_path, dst_path)
                copied += 1
            except Exception as e:
                print(f"  [錯誤] {rel_path}: {e}")
                errors += 1

    if copied > 0 or errors > 0:
        print(f"  備份完成：{copied} 個檔案，{errors} 個錯誤")
    else:
        print("  無變更")

    return True


def auto_backup_loop():
    """自動備份主迴圈"""
    print("=" * 50)
    print("自動備份系統啟動")
    print(f"來源: {SOURCE_DIR}")
    print(f"目標: {BACKUP_DIR}")
    print(f"間隔: {BACKUP_INTERVAL} 秒")
    print("按 Ctrl+C 停止")
    print("=" * 50)

    try:
        while True:
            backup_files()
            time.sleep(BACKUP_INTERVAL)
    except KeyboardInterrupt:
        print("\n\n備份系統已停止")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--once":
            # 執行一次備份
            backup_files()
        elif sys.argv[1] == "--interval" and len(sys.argv) > 2:
            # 自訂間隔
            BACKUP_INTERVAL = int(sys.argv[2])
            auto_backup_loop()
        else:
            print("用法:")
            print("  python auto_backup.py              # 每60秒自動備份")
            print("  python auto_backup.py --once        # 執行一次")
            print("  python auto_backup.py --interval 30 # 每30秒備份")
    else:
        auto_backup_loop()
