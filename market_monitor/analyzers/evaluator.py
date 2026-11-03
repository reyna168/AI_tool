from datetime import datetime

class MarketEvaluator:
    @staticmethod
    def synthesize_report(vix, cb, ipo, calendar, news, rates):
        today_str = datetime.now().strftime("%Y-%m-%d")
        
        # 綜合市場氛圍摘要
        vix_val = vix.get("vix_close", 0) if vix else 0
        vix_level = vix.get("risk_level", "未取得") if vix else "未取得"
        spread_val = rates.get("rate_spread", 0) if rates else 0

        # 計算今日重點警示數量
        punish_count = len(news.get("punish_list", [])) if news else 0
        high_yield_count = len(calendar.get("high_yield_dividends", [])) if calendar else 0
        ipo_count = len(ipo) if ipo else 0
        cb_itm_count = len(cb.get("itm_expiring", [])) if cb else 0

        summary_headline = (
            f"【晨報亮點】恐慌指標 VIX 報 {vix_val} ({vix_level.split()[0]})，"
            f"美台利差維持 {spread_val}%；"
            f"可轉債有 {cb_itm_count} 檔到期前現股站上轉換價；"
            f"今日注意/處置股共 {punish_count} 檔，"
            f"未來兩週有 {high_yield_count} 檔高息股 (>5%) 除息與 {ipo_count} 檔新股即將掛牌。"
        )

        return {
            "date": today_str,
            "headline": summary_headline,
            "vix": vix,
            "cb": cb,
            "ipo": ipo,
            "calendar": calendar,
            "news": news,
            "rates": rates
        }

