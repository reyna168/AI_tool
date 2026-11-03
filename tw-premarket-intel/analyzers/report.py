"""把各 collector 結果整合成結構化 report（失敗模組以 warnings 呈現，不中斷）。"""
from analyzers.cb_screen import screen


def build(ctx, results):
    rep = {"date": ctx.today.isoformat(), "warnings": [], "sections": {}}
    for name, res in results.items():
        if not res["ok"]:
            rep["warnings"].append(f"[{name}] 本次資料取得失敗：{res['error']}")
            continue
        data = res["data"]
        rep["sections"][name] = data
        for w in data.get("warnings", []) + data.get("errors", []):
            rep["warnings"].append(f"[{name}] {w}")
    cb = rep["sections"].get("cb")
    if cb:
        picks, counts = screen(cb["rows"], ctx.cfg, ctx.today, ctx.db)
        cb["picks"], cb["pick_counts"] = picks, counts
    return rep
