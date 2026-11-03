"""過濾例行公告：回傳 (分數, 標籤)。分數 0 代表丟棄。"""


def classify(n, cfg, keep_codes):
    subj = n["subject"]
    tags = []
    score = 0
    if n["kind"] == "disposal":
        score += 5; tags.append("處置股")
    elif n["kind"] == "watch":
        score += 3; tags.append("注意股")
    hits = [k for k in cfg["keep_keywords"] if k in subj]
    if hits:
        score += 2 + len(hits); tags += hits[:3]
    elif n["kind"] == "major" and any(k in subj for k in cfg["drop_keywords"]):
        return 0, []
    if n["code"] in keep_codes:
        score += 4; tags.append("自選/CB發行")
    if n["kind"] == "major" and score == 0:
        return 0, []          # 重訊沒命中任何關鍵字：視為雜訊
    return score, tags
