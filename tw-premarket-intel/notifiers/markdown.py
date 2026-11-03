"""Markdown 日報渲染與本機存檔。"""
import os


def _f(v, nd=2, suf=""):
    return "—" if v is None else f"{v:.{nd}f}{suf}"


def render(rep):
    s, L = rep["sections"], []
    L.append(f"# 📈 台股盤前情報 {rep['date']}\n")
    if "vix" in s:
        v = s["vix"]
        pct = f"，歷史位階 {v['percentile']}%" if v["percentile"] is not None else ""
        L += ["## 🌡️ VIX 恐慌指數",
              f"{v['light']} **{v['close']:.2f}**（{v['label']}）｜5 日變化 {v['chg5_pct']:+.1f}%{pct}｜{v['date']}\n"]
    if "rates" in s:
        r = s["rates"]
        L += ["## 🏦 台美利率與利差",
              f"- Fed 有效利率：**{_f(r['fed_funds'])}%**（{r['fed_date']}）",
              f"- 美國 10Y：**{_f(r['us10y'])}%**（{r['us10y_date']}）",
              f"- 台灣重貼現率：{_f(r['tw_discount'])}%｜台灣 10Y：{_f(r['tw_10y'])}%（手動維護，as_of {r['tw_as_of'] or '未填'}）"]
        if "spread_10y" in r:
            L.append(f"- 美台 10Y 利差：**{r['spread_10y']:+.2f}%** — {r['spread_view']}")
        if "fed_vs_discount" in r:
            L.append(f"- Fed − 重貼現率：{r['fed_vs_discount']:+.3f}%")
        L.append("")
    if "cb" in s:
        cb = s["cb"]
        L += [f"## 💱 可轉債精選（全量 {cb['total']} 檔已入庫，可算溢價 {cb['with_premium']} 檔）"]
        titles = {"discount": "低溢價 / 負溢價", "defensive": "百元以下防守型",
                  "event": "到期 / 賣回 / 贖回", "new": "新發行 / 近期掛牌"}
        for k, t in titles.items():
            items = cb["picks"][k]
            L.append(f"\n**{t}**（符合 {cb['pick_counts'][k]} 檔，列前 {len(items)}）")
            if not items:
                L.append("_今日無_")
                continue
            L += ["| 代碼 | 名稱 | CB價 | 溢價率 | 量 | 備註 |", "|---|---|---|---|---|---|"]
            for r in items:
                note = r.get("event_note", "")
                if r.get("premium_pct_rank") is not None:
                    note += f" 溢價歷史PR{r['premium_pct_rank']}"
                L.append(f"| {r['code']} | {r.get('name') or ''} | {_f(r.get('price'))} | "
                         f"{_f(r.get('premium'), 2, '%')} | {_f(r.get('volume'), 0)} | {note} |")
        L.append("")
    if "ipo" in s:
        L.append("## 🆕 未來 14 天新股（申購/抽籤/掛牌）")
        items = s["ipo"]["items"]
        if not items:
            L.append("_無_")
        for e in items:
            d = e["detail"]
            L.append(f"- **{e['date']}** {e['code']} {e['name']}（{d.get('market') or ''}）承銷價 {_f(d.get('price'))}"
                     f"｜申購 {d.get('start') or '?'}~{d.get('end') or '?'}｜抽籤 {d.get('draw') or '?'}｜掛牌 {d.get('list') or '?'}")
        L.append("")
    if "calendar" in s:
        c = s["calendar"]
        L.append("## 🗓️ 除權息（🔥 = 本次殖利率達門檻）")
        if not c["exdiv"]:
            L.append("_無_")
        for e in c["exdiv"][:40]:
            fire = "🔥 " if e["high_yield"] else ""
            L.append(f"- {fire}{e['date']} {e['code']} {e.get('name') or ''}（{e['market']}/{e['kind']}）"
                     f"價值 {_f(e['dividend'])}｜殖利率 {_f(e['yield_pct'], 2, '%')}")
        L.append("\n## 🎤 法說會")
        if not c["conferences"]:
            L.append("_無_")
        for e in c["conferences"][:40]:
            L.append(f"- {e['date']} {e['code']} {e.get('name') or ''}（{e['market']}）")
        L.append("")
    if "notices" in s:
        n = s["notices"]
        L.append(f"## ⚠️ 特別訊息（精選 {len(n['items'])} / 命中 {n['total_picked']}）")
        if not n["items"]:
            L.append("_無_")
        for x in n["items"]:
            L.append(f"- [{'/'.join(x['tags'][:3])}] {x['code']} {x.get('name') or ''}：{x['subject']}（{x['source']}）")
        L.append("")
    if rep["warnings"]:
        L.append("## 🛠️ 執行警告")
        L += [f"- {w}" for w in rep["warnings"]]
    L.append("\n> 僅為資訊整理，非投資建議。")
    return "\n".join(L)


def save(text, report_dir, day):
    os.makedirs(report_dir, exist_ok=True)
    p = os.path.join(report_dir, f"{day}.md")
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
    return p
