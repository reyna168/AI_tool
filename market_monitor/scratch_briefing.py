import requests
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
url = "https://www.twse.com.tw/zh/about/news/event/content.html?8a8216d6a0fa351b01a1808eba6e024d"
html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}).text

forms = re.findall(r'<form[^>]*>', html)
for f in forms:
    print(f)
