"""防禦型請求中介層：每網站節流 + 指數退避重試 + SQLite 當日快取。"""
import hashlib
import json
import logging
import random
import time
import datetime as dt
from urllib.parse import urlparse

import requests

log = logging.getLogger("http")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")


class Fetcher:
    def __init__(self, db, cfg):
        h = cfg.get("http", {})
        self.db = db
        self.min_i = h.get("min_interval", 1.0)
        self.max_i = h.get("max_interval", 2.0)
        self.retries = h.get("retries", 3)
        self.timeout = h.get("timeout", 20)
        self.verify = h.get("ssl_verify", True)
        self.s = requests.Session()
        self.s.headers.update({"User-Agent": UA, "Accept": "application/json, text/csv, */*"})
        self._last = {}

    def _throttle(self, url):
        host = urlparse(url).netloc
        gap = random.uniform(self.min_i, self.max_i)
        wait = gap - (time.time() - self._last.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        self._last[host] = time.time()

    def get_text(self, url, params=None, use_cache=True, validator=None):
        key = hashlib.sha1((url + json.dumps(params, sort_keys=True, default=str)).encode()).hexdigest()
        day = dt.date.today().isoformat()
        if use_cache:
            hit = self.db.cache_get(key, day)
            if hit is not None:
                log.debug("cache hit %s", url)
                return hit
        last = None
        for i in range(self.retries):
            self._throttle(url)
            try:
                r = self.s.get(url, params=params, timeout=self.timeout, verify=self.verify)
                if r.status_code == 200:
                    text = r.content.decode("utf-8-sig", errors="replace")
                    if validator is None or validator(text):
                        self.db.cache_put(key, day, text)
                        return text
                    last = RuntimeError("response failed validation")
                else:
                    last = RuntimeError(f"HTTP {r.status_code}")
            except requests.RequestException as e:
                last = e
            wait = 2 ** (i + 1)
            log.warning("GET %s failed (%s), retry in %ss", url, last, wait)
            time.sleep(wait)
        raise RuntimeError(f"GET {url} failed after {self.retries} tries: {last}")

    def get_json(self, url, params=None, **kw):
        return json.loads(self.get_text(url, params, **kw))
