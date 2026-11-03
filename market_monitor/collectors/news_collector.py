from datetime import datetime
from collectors.base_collector import BaseCollector, logger

class NewsCollector(BaseCollector):
    def fetch_special_alerts(self):
        today_str = datetime.now().strftime("%Y-%m-%d")

        # 1. 處置股票公布
        punish_url = "https://openapi.twse.com.tw/v1/announcement/punish"
        punish_raw = self.fetch_with_retry(punish_url, cache_key="announcement_punish", today_str=today_str) or []

        # 2. 注意股票公布
        notice_url = "https://openapi.twse.com.tw/v1/announcement/notice"
        notice_raw = self.fetch_with_retry(notice_url, cache_key="announcement_notice", today_str=today_str) or []

        alerts = {
            "punish_list": [],
            "notice_list": []
        }

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            # 處理處置股 (嚴重度高：預收款券、人工撮合)
            for item in punish_raw:
                code = item.get("Code", "")
                name = item.get("Name", "")
                reason = item.get("DispositionReason", item.get("Reason", "累積達處置標準"))
                measures = item.get("DisposalMeasure", "分盤撮合/預收款券")
                if code:
                    cursor.execute("""
                        INSERT INTO special_alerts (alert_date, category, code, name, reason, detail, recorded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (today_str, "DISPOSITION", code, name, reason, measures, today_str))
                    alerts["punish_list"].append({
                        "code": code, "name": name, "reason": reason, "detail": measures
                    })

            # 處理注意股 (波動過大)
            for item in notice_raw:
                code = item.get("Code", "")
                name = item.get("Name", "")
                reason = item.get("NoticeReason", item.get("Reason", "近六日漲跌幅過大或周轉率過高"))
                if code:
                    cursor.execute("""
                        INSERT INTO special_alerts (alert_date, category, code, name, reason, detail, recorded_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (today_str, "NOTICE", code, name, reason, "", today_str))
                    alerts["notice_list"].append({
                        "code": code, "name": name, "reason": reason
                    })

            conn.commit()

        logger.info(f"Special alerts collected: {len(alerts['punish_list'])} disposition, {len(alerts['notice_list'])} notice")
        return alerts

