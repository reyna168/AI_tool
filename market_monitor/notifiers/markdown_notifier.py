from pathlib import Path
from config import REPORTS_DIR

class MarkdownNotifier:
    @staticmethod
    def generate_report(data):
        date_str = data["date"]
        report_path = REPORTS_DIR / f"morning_report_{date_str}.md"

        vix = data.get("vix") or {}
        rates = data.get("rates") or {}
        cb = data.get("cb") or {}
        ipo = data.get("ipo") or []
        cal = data.get("calendar") or {}
        news = data.get("news") or {}

        lines = [
            f"# 📊 每日市場盤前情報晨報 ({date_str})",
            "",
            f"> 💡 **核心速覽**：{data['headline']}",
            "",
            "---",
            "",
            "## 1. 🌐 宏觀風險與市場情緒指標",
            "",
            f"- **CBOE VIX 恐慌指標**：`{vix.get('vix_close', 'N/A')}` （前日變動 `{vix.get('vix_change_pct', 0):+}%`）",
            f"  - 風險等級：{vix.get('risk_level', '未提供')}",
            f"- **美債 10 年期殖利率**：`{rates.get('us_10y_yield', 'N/A')}%`",
            f"- **美台政策利差**：聯準會基準 `{rates.get('us_fed_rate', 'N/A')}%` vs 台灣央行 `{rates.get('tw_central_rate', 'N/A')}%` （利差：`{rates.get('rate_spread', 'N/A')}%`）",
            f"  - 趨勢解析：{rates.get('trend_comment', '')}",
            "",
            "---",
            "",
            "## 2. 💎 可轉債 (CB) 機會雷達",
            ""
        ]

        # 1. 核心新增：即將到期且現股站上轉換價
        itm_cb = cb.get("itm_expiring", [])
        if itm_cb:
            lines.append("### 🎯 到期前現股站上轉換價標的 (強烈轉股誘因／潛在套利或賣壓)")
            lines.append("| 債券代號 | 標的名稱 | 現股收盤價 | 轉換價 | 價內溢價率 | 到期日 | 剩餘天數 |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            for item in itm_cb[:10]:
                lines.append(f"| {item['bond_code']} | {item['name']} | **{item['stock_price']}** 元 | {item['conv_price']} 元 | +{item['itm_pct']}% | {item['maturity_date']} | **{item['days_left']} 天** |")
            lines.append("")
        else:
            lines.append("### 🎯 到期前現股站上轉換價標的\n- 今日無一年內到期且現股高於轉換價之標的。\n")

        # 負溢價套利機會
        neg_cb = cb.get("negative_premium", [])
        if neg_cb:
            lines.append("### ⚡ 負折溢價／套利機會標的")
            lines.append("| 代號 | 債券名稱 | CB 收盤價 | 理論平價 | 折溢價率 |")
            lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for item in neg_cb[:5]:
                lines.append(f"| {item['code']} | {item['name']} | {item['price']} | {item['parity']} | {item['premium_rate']}% |")
            lines.append("")
        else:
            lines.append("### ⚡ 負折溢價／套利機會標的\n- 今日暫無顯著負溢價標的。\n")

        # 破百元防守標的
        under_par = cb.get("under_par", [])
        if under_par:
            lines.append("### 🛡️ 百元面額以下低檔防守型 CB")
            lines.append("| 代號 | 債券名稱 | CB 收盤價 | 溢價率 |")
            lines.append("| :--- | :--- | :--- | :--- |")
            for item in under_par[:5]:
                lines.append(f"| {item['code']} | {item['name']} | {item['price']} | {item['premium_rate']}% |")
            lines.append("")
        else:
            lines.append("### 🛡️ 百元面額以下低檔防守型 CB\n- 今日無新破百活絡標的。\n")

        lines.extend([
            "---",
            "",
            "## 3. 🚀 即將上市櫃新股 (IPO 行事曆 - 未來 14 天)",
            ""
        ])

        if ipo:
            lines.append("| 代號 | 股票名稱 | 市場類別 | 承銷價格 | 預計掛牌日 | 剩餘天數 |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for item in ipo:
                lines.append(f"| {item['code']} | {item['name']} | {item['market_type']} | {item['issue_price']} | {item['listing_date']} | {item['days_left']} 天 |")
            lines.append("")
        else:
            lines.append("- 近期 14 天內無即將掛牌上市櫃新股。\n")

        lines.extend([
            "---",
            "",
            "## 4. 📅 除權除息與重大法說會預告 (未來 14 天)",
            ""
        ])

        high_yield = cal.get("high_yield_dividends", [])
        if high_yield:
            lines.append("### 💰 高現金殖利率標的 (殖利率 > 5%)")
            lines.append("| 代號 | 股票名稱 | 除息日 | 現金股利 | 股票股利 | 預估殖利率 |")
            lines.append("| :--- | :--- | :--- | :--- | :--- | :--- |")
            for item in high_yield[:8]:
                lines.append(f"| {item['code']} | {item['name']} | {item['date']} | {item['cash_div']} 元 | {item['stock_div']} | **{item['est_yield']}%** |")
            lines.append("")
        
        reg_div = cal.get("regular_dividends", [])
        if reg_div:
            lines.append("### 📋 其他近期即將除權息標的")
            lines.append(f"- 共有 {len(reg_div)} 檔一般標的即將除息，已記錄於本地資料庫中。")
            lines.append("")

        lines.extend([
            "---",
            "",
            "## 5. ⚠️ 今日特別訊息與監管名單 (處置/注意股票)",
            ""
        ])

        punish = news.get("punish_list", [])
        if punish:
            lines.append("### 🛑 處置股票名單 (分盤撮合/預收款券)")
            for p in punish[:5]:
                lines.append(f"- **{p['code']} {p['name']}**：處置措施「{p['detail']}」，原因：{p['reason']}")
            lines.append("")
        else:
            lines.append("- 今日無新增重大處置股票。\n")

        notice = news.get("notice_list", [])
        if notice:
            lines.append(f"### 🔔 注意股票公布\n- 今日共公布 **{len(notice)} 檔** 注意股票（已同步留存至資料庫）。\n")

        lines.extend([
            "---",
            "",
            f"*本報告由本地 Market Monitor 於 {date_str} 自動彙整生成，供個人投資策略輔助參考。*"
        ])

        content = "\n".join(lines)
        report_path.write_text(content, encoding="utf-8")
        return str(report_path)

