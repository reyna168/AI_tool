import time
import json
import logging
import requests
from config import USER_AGENT, REQUEST_TIMEOUT, REQUEST_DELAY_SECONDS, MAX_RETRIES

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("MarketMonitor")

class BaseCollector:
    def __init__(self, db):
        self.db = db
        self.headers = {
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def fetch_with_retry(self, url, params=None, cache_key=None, today_str=None):
        if cache_key and today_str:
            cached = self.db.get_cache(cache_key, today_str)
            if cached:
                try:
                    return json.loads(cached)
                except Exception:
                    pass

        # 請求節流
        time.sleep(REQUEST_DELAY_SECONDS)

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, params=params, headers=self.headers, timeout=REQUEST_TIMEOUT)
                if resp.status_code == 200:
                    data = resp.json()
                    if cache_key:
                        self.db.set_cache(cache_key, json.dumps(data, ensure_ascii=False))
                    return data
                elif resp.status_code == 429:
                    logger.warning(f"Rate limited on {url}, backing off... (attempt {attempt})")
                    time.sleep(attempt * 3)
                else:
                    logger.warning(f"HTTP {resp.status_code} fetching {url}")
            except Exception as e:
                logger.error(f"Error fetching {url} on attempt {attempt}: {e}")
                time.sleep(attempt * 2)

        return None

