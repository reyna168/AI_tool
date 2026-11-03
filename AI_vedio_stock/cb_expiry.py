#!/usr/bin/env python3
"""台灣可轉債（CB）到期 / 即將到期監控。

資料來源（官方 OpenAPI，端點取自 https://www.tpex.org.tw/openapi/swagger.json）：
  - 櫃買中心  /bond_ISSBD5_data          轉(交)換債發行資料（到期日、賣回日、發行總額、目前餘額、發行時轉換價）
  - 櫃買中心  /tpex_mainboard_quotes     上櫃股票收盤行情
  - 證交所    /v1/exchangeReport/STOCK_DAY_ALL  上市股票日成交資訊

限制（請務必留意）：
  1. 官方發行資料只有「發行時轉換價格」，不含目前轉換價（可能因除權息、重設而調整）。
     要精準計算轉換價值，請用 --conv-csv 補上最新轉換價。
  2. 官方 OpenAPI 沒有 CB 市價，因此不計算溢價率。
  3. 欄位名稱可能改版：對不到時程式會印出實際欄位，修改 COLUMN_CANDIDATES 即可。

用法：
  python cb_expiry.py --within-days 60 --include-past 30 --out cb_expiry.csv
  python cb_expiry.py --within-days 90 --std-csv cb_std.csv     # 產出可餵給 screen_cb.py 的標準格式
  python cb_expiry.py --input-json sample.json                    # 離線測試
"""
import argparse
import json
import os
import re
import sys

import pandas as pd
import requests

TPEX_BASE = "https://www.tpex.org.tw/openapi/v1"
ENDPOINTS = {
    "cb_issue": f"{TPEX_BASE}/bond_ISSBD5_data",
    "tpex_stock": f"{TPEX_BASE}/tpex_mainboard_quotes",
    "twse_stock": "https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL",
}

# 標準欄位 -> 可能的來源欄位名稱（依序嘗試，其次用關鍵字模糊比對）
COLUMN_CANDIDATES = {
    "bond_code": ["債券代碼", "債券代號", "BondCode", "bond_code"],
    "bond_name": ["債券簡稱", "債券名稱", "BondShortName", "BondName"],
    "issue_date": ["發行日期", "IssueDate"],
    "maturity_date": ["到期日期", "到期日", "MaturityDate"],
    "put_date": ["賣回權日期", "賣回日期", "PutDate"],
    "issue_total": ["發行總額", "IssueAmount"],
    "balance": ["目前餘額", "最新餘額", "Balance"],
    "issue_conv_price": ["發行時轉換價格", "發行時轉換價", "ConversionPrice"],
}
FUZZY_KEYWORDS = {
    "bond_code": ["債券代"],
    "bond_name": ["簡稱"],
    "maturity_date": ["到期"],
    "put_date": ["賣回權日"],
    "issue_total": ["發行總額"],
    "balance": ["目前餘額"],
    "issue_conv_price": ["轉換價"],
}


def get_json(url):
    r = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.json()


def parse_date(v):
    """支援 2026-10-18 / 2026/10/18 / 20261018 / 1151018 / 115/10/18 / 115-10-18。"""
    if v is None:
        return pd.NaT
    s = str(v).strip()
    if not s or s.lower() in ("nan", "none", "-", "n/a"):
        return pd.NaT
    m = re.fullmatch(r"(\d{2,4})[-/.](\d{1,2})[-/.](\d{1,2})", s)
    if m:
        y, mo, d = map(int, m.groups())
    elif re.fullmatch(r"\d{8}", s):
        y, mo, d = int(s[:4]), int(s[4:6]), int(s[6:])
    elif re.fullmatch(r"\d{6,7}", s):          # 民國 YYYMMDD
        y, mo, d = int(s[:-4]), int(s[-4:-2]), int(s[-2:])
    else:
        return pd.NaT
    if y < 1911:                                # 民國年
        y += 1911
    try:
        return pd.Timestamp(year=y, month=mo, day=d)
    except ValueError:
        return pd.NaT


def to_num(v):
    return pd.to_numeric(str(v).replace(",", "").strip(), errors="coerce")


def map_columns(df):
    mapping = {}
    for std, cands in COLUMN_CANDIDATES.items():
        hit = next((c for c in cands if c in df.columns), None)
        if hit is None:
            kws = FUZZY_KEYWORDS.get(std, [])
            hit = next((c for c in df.columns if any(k in str(c) for k in kws)), None)
        if hit is not None:
            mapping[std] = hit
    missing = [k for k in ("bond_code", "maturity_date") if k not in mapping]
    if missing:
        sys.exit(
            f"對不到必要欄位 {missing}。API 實際欄位如下，請修改 COLUMN_CANDIDATES：\n"
            + ", ".join(map(str, df.columns))
        )
    out = pd.DataFrame({std: df[src] for std, src in mapping.items()})
    for std in COLUMN_CANDIDATES:
        if std not in out.columns:
            out[std] = None
    return out


def load_stock_prices():
    """回傳 {股票代號: (名稱, 收盤價)}；抓不到就回傳空 dict，不中斷。"""
    prices = {}
    for key, code_k, name_k, px_k in [
        ("tpex_stock", "SecuritiesCompanyCode", "CompanyName", "Close"),
        ("twse_stock", "Code", "Name", "ClosingPrice"),
    ]:
        try:
            for row in get_json(ENDPOINTS[key]):
                px = to_num(row.get(px_k))
                prices[str(row.get(code_k, "")).strip()] = (row.get(name_k), px)
        except Exception as e:  # noqa: BLE001
            print(f"[警告] 取得 {key} 股價失敗：{e}", file=sys.stderr)
    return prices


def build(df_raw, today, within_days, past_days, conv_csv=None, with_prices=True):
    df = map_columns(df_raw)
    df["bond_code"] = df["bond_code"].astype(str).str.strip()
    for c in ("maturity_date", "put_date", "issue_date"):
        df[c] = df[c].map(parse_date)
    for c in ("issue_total", "balance", "issue_conv_price"):
        df[c] = df[c].map(to_num)

    df["days_to_maturity"] = (df["maturity_date"] - today).dt.days
    df["days_to_put"] = (df["put_date"] - today).dt.days
    df["outstanding_pct"] = (df["balance"] / df["issue_total"] * 100).round(2)

    # 標的股票代號：CB 代號前 4 碼（例：36804 -> 3680）。此為通用慣例，極少數例外請自行核對。
    df["stock_code"] = df["bond_code"].str[:4]

    if conv_csv:
        ov = pd.read_csv(conv_csv, dtype={"bond_code": str})[["bond_code", "conv_price"]]
        df = df.merge(ov, on="bond_code", how="left")
        df["conv_price"] = df["conv_price"].fillna(df["issue_conv_price"])
    else:
        df["conv_price"] = df["issue_conv_price"]

    prices = load_stock_prices() if with_prices else {}
    df["stock_name"] = df["stock_code"].map(lambda c: (prices.get(c) or (None, None))[0])
    df["stock_price"] = df["stock_code"].map(lambda c: (prices.get(c) or (None, None))[1])
    df["parity"] = (df["stock_price"] / df["conv_price"] * 100).round(2)

    mask = df["days_to_maturity"].between(-past_days, within_days)
    return df[mask].sort_values("maturity_date").reset_index(drop=True)


def push_telegram(text):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print("[略過推播] 未設定 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID", file=sys.stderr)
        return
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": text[:4000]},
        timeout=30,
    )
    r.raise_for_status()


def to_message(res, today):
    if res.empty:
        return f"{today:%Y-%m-%d} 範圍內沒有到期的 CB。"
    lines = [f"CB 到期監控 {today:%Y-%m-%d}（共 {len(res)} 檔）"]
    for _, r in res.iterrows():
        par = "" if pd.isna(r["parity"]) else f"，轉換價值約 {r['parity']:.1f}"
        pct = "" if pd.isna(r["outstanding_pct"]) else f"，餘額 {r['outstanding_pct']:.1f}%"
        lines.append(
            f"{r['maturity_date']:%m/%d} {r['bond_code']} {r['bond_name']}"
            f"（剩 {int(r['days_to_maturity'])} 天{pct}{par}）"
        )
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="台灣 CB 到期監控")
    ap.add_argument("--within-days", type=int, default=60, help="未來 N 天內到期（預設 60）")
    ap.add_argument("--include-past", type=int, default=0, help="一併列出過去 N 天內已到期（預設 0）")
    ap.add_argument("--today", help="指定今天 YYYY-MM-DD（測試用）")
    ap.add_argument("--conv-csv", help="補最新轉換價的 CSV（欄位：bond_code,conv_price）")
    ap.add_argument("--no-prices", action="store_true", help="不抓股價")
    ap.add_argument("--input-json", help="改讀本機 JSON（離線測試）")
    ap.add_argument("--out", help="輸出完整結果 CSV")
    ap.add_argument("--std-csv", help="輸出 screen_cb.py 標準格式 CSV")
    ap.add_argument("--telegram", action="store_true", help="推播摘要到 Telegram")
    a = ap.parse_args()

    today = pd.Timestamp(a.today) if a.today else pd.Timestamp.today().normalize()
    if a.input_json:
        with open(a.input_json, encoding="utf-8") as f:
            raw = pd.DataFrame(json.load(f))
    else:
        raw = pd.DataFrame(get_json(ENDPOINTS["cb_issue"]))
    if raw.empty:
        sys.exit("API 沒有回傳資料。")

    res = build(raw, today, a.within_days, a.include_past, a.conv_csv, not a.no_prices)

    show = ["bond_code", "bond_name", "stock_code", "stock_name", "stock_price",
            "conv_price", "parity", "maturity_date", "days_to_maturity",
            "put_date", "days_to_put", "outstanding_pct"]
    print(f"資料日期：{today:%Y-%m-%d}；範圍：過去 {a.include_past} 天 ~ 未來 {a.within_days} 天；共 {len(res)} 檔")
    print("註：conv_price 為『發行時轉換價』（除非用 --conv-csv 覆蓋），parity 僅供參考。")
    print(res[show].to_string(index=False))

    if a.out:
        res.to_csv(a.out, index=False, encoding="utf-8-sig")
        print(f"已輸出 {a.out}", file=sys.stderr)
    if a.std_csv:
        std = res.assign(bond_price=None)[[
            "bond_code", "bond_name", "stock_code", "stock_name", "bond_price",
            "conv_price", "stock_price", "maturity_date", "put_date", "outstanding_pct"]]
        std.to_csv(a.std_csv, index=False, encoding="utf-8-sig", date_format="%Y-%m-%d")
        print(f"已輸出標準格式 {a.std_csv}", file=sys.stderr)
    if a.telegram:
        push_telegram(to_message(res, today))


if __name__ == "__main__":
    main()
