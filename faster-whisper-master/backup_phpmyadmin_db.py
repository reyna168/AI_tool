#!/usr/bin/env python3
"""
backup_phpmyadmin_db.py
------------------------
備份 phpMyAdmin 使用的 MySQL 資料庫（預設資料庫名稱: phpmyadmin，
存放書籤、SQL 查詢歷史、使用者偏好設定等 phpMyAdmin 設定儲存表 pma__*）。

用法:
    # 最簡單：用環境變數帶密碼
    export MYSQL_PASSWORD="你的密碼"
    python backup_phpmyadmin_db.py --host 127.0.0.1 --user root

    # 全部參數自訂
    python backup_phpmyadmin_db.py \\
        --host 127.0.0.1 --port 3306 --user root \\
        --database chengshiusystem \\
        --output-dir ./backups \\
        --retention-days 7 \\
        --mysqldump-path "C:/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe"

密碼優先順序: --password 參數 > MYSQL_PASSWORD 環境變數 > 互動輸入
"""
import argparse
import getpass
import gzip
import logging
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("phpmyadmin_backup")


def parse_args():
    parser = argparse.ArgumentParser(description="備份 phpMyAdmin 資料庫")
    parser.add_argument("--host", default="127.0.0.1", help="MySQL 主機 (預設 127.0.0.1)")
    parser.add_argument("--port", type=int, default=3306, help="MySQL 連接埠 (預設 3306)")
    parser.add_argument("--user", default="root", help="MySQL 使用者 (預設 root)")
    parser.add_argument("--password", default=None, help="MySQL 密碼（不建議直接寫在指令列，優先用環境變數）")
    parser.add_argument("--database", default="phpmyadmin",
                         help="要備份的資料庫名稱 (預設 phpmyadmin，也就是 phpMyAdmin 設定儲存庫)")
    parser.add_argument("--output-dir", default="./backups", help="備份輸出目錄")
    parser.add_argument("--retention-days", type=int, default=7, help="保留天數，超過自動刪除舊備份 (0 = 不清除)")
    parser.add_argument("--no-compress", action="store_true", help="不要 gzip 壓縮，直接留 .sql")
    parser.add_argument("--mysqldump-path", default="mysqldump",
                         help="mysqldump 執行檔路徑，Windows 常需填完整路徑，"
                              "例如 C:/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe")
    return parser.parse_args()


def resolve_password(args) -> str:
    if args.password:
        return args.password
    env_pwd = os.environ.get("MYSQL_PASSWORD")
    if env_pwd:
        return env_pwd
    # 都沒有的話，安全地互動輸入（不會顯示在畫面上）
    return getpass.getpass(f"請輸入 MySQL 使用者 '{args.user}' 的密碼: ")


def cleanup_old_backups(output_dir: str, retention_days: int, prefix: str):
    if retention_days <= 0 or not os.path.isdir(output_dir):
        return
    cutoff = time.time() - retention_days * 86400
    removed = []
    for fname in os.listdir(output_dir):
        if not fname.startswith(prefix):
            continue
        fpath = os.path.join(output_dir, fname)
        if os.path.isfile(fpath) and os.path.getmtime(fpath) < cutoff:
            try:
                os.remove(fpath)
                removed.append(fname)
            except OSError as e:
                logger.warning("刪除舊備份失敗 %s: %s", fpath, e)
    if removed:
        logger.info("已清除 %d 個超過 %d 天的舊備份: %s", len(removed), retention_days, removed)


def run_backup(args) -> str:
    password = resolve_password(args)
    os.makedirs(args.output_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = f"{args.database}_"
    sql_filename = f"{prefix}{ts}.sql"
    sql_path = os.path.join(args.output_dir, sql_filename)

    cmd = [
        args.mysqldump_path,
        "-h", str(args.host),
        "-P", str(args.port),
        "-u", str(args.user),
        "--single-transaction",
        "--quick",
        args.database,
    ]

    env = os.environ.copy()
    env["MYSQL_PWD"] = password  # 用環境變數傳密碼，避免出現在系統的 process 列表中

    logger.info("開始備份資料庫 '%s' (host=%s:%s) -> %s", args.database, args.host, args.port, sql_path)
    try:
        with open(sql_path, "wb") as out_f:
            result = subprocess.run(cmd, stdout=out_f, stderr=subprocess.PIPE, env=env)
    except FileNotFoundError:
        if os.path.exists(sql_path):
            os.remove(sql_path)
        logger.error(
            "找不到 mysqldump 執行檔: '%s'。"
            "Windows 上請用 --mysqldump-path 指定完整路徑，"
            "例如: C:/Program Files/MySQL/MySQL Server 8.0/bin/mysqldump.exe",
            args.mysqldump_path,
        )
        sys.exit(1)

    if result.returncode != 0:
        if os.path.exists(sql_path):
            os.remove(sql_path)
        err_msg = result.stderr.decode("utf-8", errors="ignore")
        logger.error("mysqldump 執行失敗:\n%s", err_msg)
        sys.exit(1)

    final_path = sql_path
    if not args.no_compress:
        gz_path = sql_path + ".gz"
        with open(sql_path, "rb") as f_in, gzip.open(gz_path, "wb") as f_out:
            shutil.copyfileobj(f_in, f_out)
        os.remove(sql_path)
        final_path = gz_path

    # 簡單驗證：檔案不能是 0 bytes，gz 檔要能正常開啟
    if os.path.getsize(final_path) == 0:
        logger.error("備份檔案大小為 0，疑似備份失敗: %s", final_path)
        sys.exit(1)
    if final_path.endswith(".gz"):
        try:
            with gzip.open(final_path, "rb") as f:
                f.read(1024)
        except OSError as e:
            logger.error("備份檔案損毀 (gzip 驗證失敗): %s (%s)", final_path, e)
            sys.exit(1)

    size_kb = os.path.getsize(final_path) / 1024
    logger.info("備份完成: %s (%.1f KB)", final_path, size_kb)

    cleanup_old_backups(args.output_dir, args.retention_days, prefix)
    return final_path


def main():
    args = parse_args()
    run_backup(args)


if __name__ == "__main__":
    main()
