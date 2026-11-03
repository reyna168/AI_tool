"""SQLite 儲存層：歷史時間序列、可轉債日資料、事件、公告、HTTP 當日快取。"""
import datetime as dt
import hashlib
import json
import os
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS http_cache(key TEXT PRIMARY KEY, day TEXT, body TEXT);
CREATE TABLE IF NOT EXISTS series(name TEXT, day TEXT, value REAL, PRIMARY KEY(name, day));
CREATE TABLE IF NOT EXISTS cb_quotes(
  day TEXT, code TEXT, name TEXT, stock_code TEXT, price REAL, conv_price REAL,
  stock_price REAL, premium REAL, volume REAL, maturity TEXT, put_date TEXT,
  issue_date TEXT, call_flag INTEGER, PRIMARY KEY(day, code));
CREATE TABLE IF NOT EXISTS events(
  kind TEXT, event_date TEXT, code TEXT, name TEXT, detail TEXT,
  PRIMARY KEY(kind, event_date, code));
CREATE TABLE IF NOT EXISTS announcements(
  hash TEXT PRIMARY KEY, day TEXT, source TEXT, code TEXT, name TEXT, subject TEXT);
"""


class DB:
    def __init__(self, path):
        d = os.path.dirname(path)
        if d:
            os.makedirs(d, exist_ok=True)
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        cutoff = (dt.date.today() - dt.timedelta(days=7)).isoformat()
        self.conn.execute("DELETE FROM http_cache WHERE day < ?", (cutoff,))
        self.conn.commit()

    # --- HTTP cache ---
    def cache_get(self, key, day):
        r = self.conn.execute("SELECT body FROM http_cache WHERE key=? AND day=?", (key, day)).fetchone()
        return r["body"] if r else None

    def cache_put(self, key, day, body):
        self.conn.execute("INSERT OR REPLACE INTO http_cache VALUES(?,?,?)", (key, day, body))
        self.conn.commit()

    # --- series ---
    def upsert_series(self, name, rows):
        self.conn.executemany("INSERT OR REPLACE INTO series VALUES(?,?,?)",
                              [(name, d, v) for d, v in rows])
        self.conn.commit()

    def series(self, name, limit=None):
        q = "SELECT day, value FROM series WHERE name=? ORDER BY day"
        rows = [(r["day"], r["value"]) for r in self.conn.execute(q, (name,))]
        return rows[-limit:] if limit else rows

    # --- CB ---
    def save_cb(self, day, rows):
        self.conn.executemany(
            "INSERT OR REPLACE INTO cb_quotes VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [(day, r["code"], r.get("name"), r.get("stock_code"), r.get("price"), r.get("conv_price"),
              r.get("stock_price"), r.get("premium"), r.get("volume"),
              r["maturity"].isoformat() if r.get("maturity") else None,
              r["put_date"].isoformat() if r.get("put_date") else None,
              r["issue_date"].isoformat() if r.get("issue_date") else None,
              1 if r.get("call_flag") else 0) for r in rows])
        self.conn.commit()

    def premium_history(self, code, limit=250):
        q = "SELECT premium FROM cb_quotes WHERE code=? AND premium IS NOT NULL ORDER BY day DESC LIMIT ?"
        return [r["premium"] for r in self.conn.execute(q, (code, limit))]

    # --- events / announcements ---
    def save_events(self, kind, rows):
        self.conn.executemany(
            "INSERT OR REPLACE INTO events VALUES(?,?,?,?,?)",
            [(kind, r["date"].isoformat(), r["code"], r.get("name"),
              json.dumps(r.get("detail", {}), ensure_ascii=False, default=str)) for r in rows])
        self.conn.commit()

    def save_announcements(self, day, source, rows):
        new = 0
        for r in rows:
            h = hashlib.sha1(f"{source}|{r['code']}|{r['subject']}".encode()).hexdigest()
            cur = self.conn.execute("INSERT OR IGNORE INTO announcements VALUES(?,?,?,?,?,?)",
                                    (h, day, source, r["code"], r.get("name"), r["subject"]))
            new += cur.rowcount
        self.conn.commit()
        return new
