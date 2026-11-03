import argparse
import sys
import time
from datetime import datetime

# 解決 Windows 主控台 Unicode / Emoji 編碼問題
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from storage.database import Database
from collectors.vix_collector import VixCollector
from collectors.cb_collector import CbCollector
from collectors.ipo_collector import IpoCollector
from collectors.calendar_collector import CalendarCollector
from collectors.news_collector import NewsCollector
from collectors.rates_collector import RatesCollector
from analyzers.evaluator import MarketEvaluator
from notifiers.markdown_notifier import MarkdownNotifier
from notifiers.telegram_notifier import TelegramNotifier
from collectors.base_collector import logger

def print_console_summary(data):
    vix = data.get("vix") or {}
    rates = data.get("rates") or {}
    news = data.get("news") or {}
    cal = data.get("calendar") or {}
    ipo = data.get("ipo") or []
    cb = data.get("cb") or {}

    print("\n" + "=" * 65)
    print(f"  📊 市場盤前情報晨報速覽 ({data['date']})")
    print("=" * 65)
    print(f"\n💡 核心亮點：\n   {data['headline']}\n")

    # 1. 宏觀指標
    print("─" * 65)
    print("【1. 宏觀風險與情緒指標】")
    print(f"  • CBOE VIX 恐慌指標 : {vix.get('vix_close', 'N/A')} (前日變動 {vix.get('vix_change_pct', 0):+}%)")
    print(f"    風險等級評級      : {vix.get('risk_level', '未取得')}")
    print(f"  • 10 年期美債殖利率 : {rates.get('us_10y_yield', 'N/A')}%")
    print(f"  • 美台政策基準利差  : {rates.get('rate_spread', 'N/A')}% (美 {rates.get('us_fed_rate', 'N/A')}% vs 台 {rates.get('tw_central_rate', 'N/A')}%)")
    print(f"    利差情勢解析      : {rates.get('trend_comment', '')}")

    # 2. 處置與注意股票
    print("\n" + "─" * 65)
    print("【2. 今日特別訊息：處置與注意股票名單】")
    punish = news.get("punish_list", [])
    if punish:
        print(f"  🛑 處置股票名單 (共 {len(punish)} 檔)：")
        for p in punish:
            print(f"     • [{p['code']}] {p['name']:<8} | 措施: {p['detail']} | 原因: {p['reason']}")
    else:
        print("  ✓ 今日無新增處置股票。")
    
    notice = news.get("notice_list", [])
    if notice:
        print(f"  🔔 注意股票公布：共 {len(notice)} 檔公布留存於資料庫。")

    # 3. 高現金殖利率除息標的
    print("\n" + "─" * 65)
    print("【3. 未來 14 天高現金殖利率除權息標的 (>5%)】")
    high_yield = cal.get("high_yield_dividends", [])
    if high_yield:
        print(f"  💰 共有 {len(high_yield)} 檔高息標的即將除息：")
        for h in high_yield:
            print(f"     • [{h['code']}] {h['name']:<8} | 除息日: {h['date']} | 現金股利: {h['cash_div']} 元 | 預估殖利率: {h['est_yield']}%")
    else:
        print("  ✓ 近期 14 天內無高於 5% 門檻之除權息標的。")

    # 4. 即將上市櫃新股
    print("\n" + "─" * 65)
    print("【4. 未來 14 天即將上市櫃新股 (IPO 行事曆)】")
    if ipo:
        print(f"  🚀 共有 {len(ipo)} 檔新股即將掛牌：")
        for item in ipo:
            print(f"     • [{item['code']}] {item['name']:<8} | 市場: {item['market_type']} | 承銷價: {item['issue_price']} 元 | 掛牌日: {item['listing_date']}")
    else:
        print("  ✓ 近期 14 天內台股主板市場暫無已排定掛牌之初次上市櫃新股。")

    # 5. 可轉債機會
    print("\n" + "─" * 65)
    print("【5. 可轉債 (CB) 機會雷達】")
    itm_cb = cb.get("itm_expiring", [])
    if itm_cb:
        print(f"  🎯 到期前現股站上轉換價 (共 {len(itm_cb)} 檔，強烈轉股/賣壓誘因)：")
        for c in itm_cb[:6]:
            print(f"     • [{c['bond_code']}] {c['name']:<8} | 現股: {c['stock_price']:>6.1f} 元 | 轉換價: {c['conv_price']:>6.1f} 元 | 價內: +{c['itm_pct']:>5.1f}% | 到期: {c['maturity_date']} (剩 {c['days_left']} 天)")
        if len(itm_cb) > 6:
            print(f"       ...其餘 {len(itm_cb) - 6} 檔標的已同步記錄於 Markdown 日報與資料庫中。")
    else:
        print("  ✓ 今日無 1 年內即將到期且現股站上轉換價之標的。")

    neg_cb = cb.get("negative_premium", [])
    under_par = cb.get("under_par", [])
    if neg_cb:
        print(f"\n  ⚡ 負折溢價套利標的 (共 {len(neg_cb)} 檔)：")
        for c in neg_cb[:5]:
            print(f"     • [{c['code']}] {c['name']:<8} | 收盤價: {c['price']} | 折溢價率: {c['premium_rate']}%")
    elif under_par:
        print(f"\n  🛡️ 破百元防守標的 (共 {len(under_par)} 檔)：")
        for c in under_par[:5]:
            print(f"     • [{c['code']}] {c['name']:<8} | 收盤價: {c['price']}")

    print("=" * 65)


def run_pipeline():
    logger.info("==========================================")
    logger.info("Starting Market Monitoring Pipeline...")
    logger.info("==========================================")
    
    db = Database()

    # 1. 採集各項數據
    logger.info("1/6 Fetching VIX Index...")
    vix_data = VixCollector(db).fetch_vix()

    logger.info("2/6 Fetching Interest Rates & Spread...")
    rates_data = RatesCollector(db).fetch_rates_and_spread()

    logger.info("3/6 Fetching Convertible Bonds (CB)...")
    cb_data = CbCollector(db).fetch_cb_data()

    logger.info("4/6 Fetching Upcoming IPOs...")
    ipo_data = IpoCollector(db).fetch_upcoming_ipos()

    logger.info("5/6 Fetching Dividends & Corporate Events...")
    calendar_data = CalendarCollector(db).fetch_dividend_and_briefings()

    logger.info("6/6 Fetching Special Alerts (Punish & Notice)...")
    news_data = NewsCollector(db).fetch_special_alerts()

    # 2. 綜合評估分析
    logger.info("Synthesizing market report...")
    synthesized = MarketEvaluator.synthesize_report(
        vix=vix_data,
        cb=cb_data,
        ipo=ipo_data,
        calendar=calendar_data,
        news=news_data,
        rates=rates_data
    )

    # 3. 輸出 Markdown 報告
    report_file = MarkdownNotifier.generate_report(synthesized)
    logger.info(f"Report generated successfully: {report_file}")

    # 4. 推送通知
    TelegramNotifier.send_summary(synthesized)

    # 5. 在終端機完整列印呈現晨報細節
    print_console_summary(synthesized)
    print(f"📁 完整詳細報告存檔路徑：{report_file}\n")
    return report_file

def start_scheduler():
    logger.info("Market Monitor scheduler started. Waiting for 07:30 daily trigger...")
    while True:
        now = datetime.now()
        # 每天 07:30 觸發
        if now.hour == 7 and now.minute == 30:
            logger.info("Triggering 07:30 daily morning run...")
            run_pipeline()
            time.sleep(70) # 避免同分鐘重複執行
        time.sleep(30)

def main():
    parser = argparse.ArgumentParser(description="市場盤前情報與宏觀指標自動監控系統")
    parser.add_argument("--now", action="store_true", help="立即執行一次完整採集並產出報告 (預設)")
    parser.add_argument("--schedule", action="store_true", help="以排程守護程序常駐，每日 07:30 自動產出")
    args = parser.parse_args()

    if args.schedule:
        start_scheduler()
    else:
        run_pipeline()

if __name__ == "__main__":
    main()
