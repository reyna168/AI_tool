"""燈號與數值換算：VIX 燈號、美台利差解讀、除息殖利率。"""
import datetime as dt


def vix_light(v, cfg):
    if v > cfg["red_above"]:
        return "🔴", "極度恐慌"
    if v > cfg["yellow_above"]:
        return "🟡", "警戒"
    if v < cfg["green_below"]:
        return "🟢", "低波動/安心"
    return "⚪", "常態震盪"


def spread_view(spread, history, today):
    """spread = 美10Y - 台10Y。與約 7 天前的快照比較趨勢。"""
    side = "美高於台，資金外流壓力" if spread > 0 else "台高於美，利差倒掛（有利資金留在台灣）"
    prior = [v for d, v in history if d <= (today - dt.timedelta(days=7)).isoformat()]
    if not prior:
        return f"{side}；趨勢：歷史累積中"
    delta = spread - prior[-1]
    trend = "擴大" if delta > 0.02 else "收斂" if delta < -0.02 else "持平"
    return f"{side}；近一週{trend}（{delta:+.2f}）"


def ex_yield(dividend, prev_close):
    """單次除權息價值 / 除權息前收盤價 (%)。權息併行時為估算上限。"""
    if not dividend or not prev_close:
        return None
    return round(dividend / prev_close * 100, 2)
