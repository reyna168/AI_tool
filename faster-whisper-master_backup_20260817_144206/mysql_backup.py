import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

# MySQL 連線設定
DB_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "your_password",  # 請改為您的密碼
}

# 要備份的資料庫列表（空列表=備份所有資料庫）
DATABASES = []  # 例如: ["mydb1", "mydb2"]

# 備份儲存目錄
BACKUP_DIR = r"C:\Users\USER\Documents\GitHub\AI_tool\faster-whisper-master\sql_backups"

# 保留備份天數
RETENTION_DAYS = 30

# 自動備份間隔（秒）
BACKUP_INTERVAL = 3600  # 1小時


def run_mysqldump(db_name, output_file):
    """執行 mysqldump 備份"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] 備份資料庫: {db_name}")

    cmd = [
        "mysqldump",
        f"--host={DB_CONFIG['host']}",
        f"--port={DB_CONFIG['port']}",
        f"--user={DB_CONFIG['user']}",
        f"--password={DB_CONFIG['password']}",
        "--single-transaction",
        "--routines",
        "--triggers",
        "--events",
        db_name,
    ]

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)

        if result.returncode == 0:
            size_mb = os.path.getsize(output_file) / (1024 * 1024)
            print(f"  完成！大小: {size_mb:.2f} MB")
            return True
        else:
            print(f"  錯誤: {result.stderr}")
            os.remove(output_file)
            return False

    except FileNotFoundError:
        print("  錯誤: 找不到 mysqldump，請確認 MySQL 已安裝並加入 PATH")
        return False
    except Exception as e:
        print(f"  錯誤: {e}")
        return False


def get_databases():
    """取得所有資料庫列表"""
    if DATABASES:
        return DATABASES

    cmd = [
        "mysql",
        f"--host={DB_CONFIG['host']}",
        f"--port={DB_CONFIG['port']}",
        f"--user={DB_CONFIG['user']}",
        f"--password={DB_CONFIG['password']}",
        "-e",
        "SHOW DATABASES;",
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            dbs = result.stdout.strip().split("\n")[1:]  # 跳過標題
            exclude = {"information_schema", "performance_schema", "mysql", "sys"}
            return [db for db in dbs if db not in exclude]
        else:
            print(f"取得資料庫列表失敗: {result.stderr}")
            return []
    except Exception as e:
        print(f"取得資料庫列表失敗: {e}")
        return []


def cleanup_old_backups():
    """清理過期備份"""
    cutoff = datetime.now().timestamp() - (RETENTION_DAYS * 86400)
    removed = 0

    for f in Path(BACKUP_DIR).glob("*.sql"):
        if f.stat().st_mtime < cutoff:
            f.unlink()
            removed += 1
            print(f"  刪除舊備份: {f.name}")

    return removed


def backup_all():
    """備份所有資料庫"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    print("=" * 50)
    print(f"開始備份 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    os.makedirs(BACKUP_DIR, exist_ok=True)

    databases = get_databases()
    if not databases:
        print("沒有找到要備份的資料庫")
        return

    print(f"要備份的資料庫: {', '.join(databases)}\n")

    success = 0
    failed = 0

    for db in databases:
        output_file = os.path.join(BACKUP_DIR, f"{db}_{timestamp}.sql")
        if run_mysqldump(db, output_file):
            success += 1
        else:
            failed += 1

    # 清理舊備份
    removed = cleanup_old_backups()

    print("\n" + "=" * 50)
    print(f"備份完成！成功: {success}, 失敗: {failed}, 清理: {removed}")
    print("=" * 50)


def auto_backup_loop():
    """自動備份主迴圈"""
    print("MySQL 自動備份系統啟動")
    print(f"備份間隔: {BACKUP_INTERVAL} 秒 ({BACKUP_INTERVAL // 60} 分鐘)")
    print(f"保留天數: {RETENTION_DAYS} 天")
    print("按 Ctrl+C 停止\n")

    try:
        while True:
            backup_all()
            print(f"\n下次備份: {BACKUP_INTERVAL} 秒後\n")
            time.sleep(BACKUP_INTERVAL)
    except KeyboardInterrupt:
        print("\n備份系統已停止")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        if sys.argv[1] == "--once":
            backup_all()
        elif sys.argv[1] == "--interval" and len(sys.argv) > 2:
            global BACKUP_INTERVAL
            BACKUP_INTERVAL = int(sys.argv[2])
            auto_backup_loop()
        elif sys.argv[1] == "--list":
            dbs = get_databases()
            print("資料庫列表:")
            for db in dbs:
                print(f"  - {db}")
        else:
            print("用法:")
            print("  python mysql_backup.py                   # 持續自動備份")
            print("  python mysql_backup.py --once            # 執行一次")
            print("  python mysql_backup.py --interval 1800   # 每30分鐘備份")
            print("  python mysql_backup.py --list            # 列出資料庫")
    else:
        auto_backup_loop()
