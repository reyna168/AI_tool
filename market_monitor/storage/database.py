import sqlite3
from datetime import datetime
from config import DB_PATH

class Database:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self._init_tables()

    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_tables(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. 每日 VIX 與宏觀指數快照
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS vix_history (
                date TEXT PRIMARY KEY,
                vix_close REAL,
                vix_change_pct REAL,
                risk_level TEXT,
                updated_at TEXT
            )
            """)

            # 2. 可轉債歷史報價與關鍵指標
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cb_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT,
                bond_code TEXT,
                bond_name TEXT,
                close_price REAL,
                premium_rate REAL,
                conversion_price REAL,
                stock_price REAL,
                features TEXT,
                UNIQUE(date, bond_code)
            )
            """)

            # 3. 即將上市櫃新股 (IPO)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS ipo_schedules (
                code TEXT,
                name TEXT,
                market_type TEXT,
                issue_price REAL,
                listing_date TEXT,
                status TEXT,
                recorded_at TEXT,
                PRIMARY KEY(code, listing_date)
            )
            """)

            # 4. 除權息與法說會行事曆
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS corporate_events (
                event_type TEXT, -- 'DIVIDEND' 或 'BRIEFING'
                event_date TEXT,
                code TEXT,
                name TEXT,
                cash_dividend REAL,
                stock_dividend REAL,
                est_yield REAL,
                description TEXT,
                recorded_at TEXT,
                PRIMARY KEY(event_type, event_date, code)
            )
            """)

            # 5. 特別訊息（注意/處置股票與重訊）
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS special_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_date TEXT,
                category TEXT, -- 'DISPOSITION', 'NOTICE', 'MATERIAL_NEWS'
                code TEXT,
                name TEXT,
                reason TEXT,
                detail TEXT,
                recorded_at TEXT
            )
            """)

            # 6. 台美利率與利差
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS interest_rates (
                date TEXT PRIMARY KEY,
                us_fed_rate REAL,
                tw_central_rate REAL,
                us_10y_yield REAL,
                rate_spread REAL,
                trend_comment TEXT,
                updated_at TEXT
            )
            """)

            # 7. 當日資料快取鎖（避免當日重複向官方發送過多請求）
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS request_cache (
                cache_key TEXT PRIMARY KEY,
                response_json TEXT,
                cached_at TEXT
            )
            """)
            conn.commit()

    def get_cache(self, key, today_str):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT response_json, cached_at FROM request_cache WHERE cache_key = ?", (key,))
            row = cursor.fetchone()
            if row and row["cached_at"].startswith(today_str):
                return row["response_json"]
        return None

    def set_cache(self, key, content_json):
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO request_cache (cache_key, response_json, cached_at)
                VALUES (?, ?, ?)
                ON CONFLICT(cache_key) DO UPDATE SET response_json=excluded.response_json, cached_at=excluded.cached_at
            """, (key, content_json, now_str))
            conn.commit()

