#!/usr/bin/env python3
"""讀取標準格式 CB CSV，計算 parity/溢價率/剩餘天數並依條件篩選。"""
import argparse, sys
import pandas as pd

def load(path, today=None):
    df = pd.read_csv(path, dtype={"bond_code": str, "stock_code": str})
    for c in ("bond_price", "conv_price", "stock_price", "outstanding_pct"):
        df[c] = pd.to_numeric(df.get(c), errors="coerce")
    today = pd.Timestamp(today) if today else pd.Timestamp.today().normalize()
    for c in ("maturity_date", "put_date"):
        df[c] = pd.to_datetime(df.get(c), errors="coerce")
    df["days_to_maturity"] = (df["maturity_date"] - today).dt.days
    df["days_to_put"] = (df["put_date"] - today).dt.days
    df["parity"] = df["stock_price"] / df["conv_price"] * 100
    df["premium_pct"] = (df["bond_price"] / df["parity"] - 1) * 100
    return df

def main():
    p = argparse.ArgumentParser()
    p.add_argument("csv")
    p.add_argument("--today")
    p.add_argument("--max-days-to-maturity", type=int)
    p.add_argument("--max-days-to-put", type=int)
    p.add_argument("--min-parity", type=float)
    p.add_argument("--max-premium", type=float)
    p.add_argument("--min-premium", type=float)
    p.add_argument("--max-outstanding", type=float)
    p.add_argument("--sort-by", default="premium_pct")
    p.add_argument("--out")
    a = p.parse_args()

    df = load(a.csv, a.today)
    m = pd.Series(True, index=df.index)
    if a.max_days_to_maturity is not None:
        m &= df.days_to_maturity.between(0, a.max_days_to_maturity)
    if a.max_days_to_put is not None:
        m &= df.days_to_put.between(0, a.max_days_to_put)
    if a.min_parity is not None:
        m &= df.parity >= a.min_parity
    if a.max_premium is not None:
        m &= df.premium_pct <= a.max_premium
    if a.min_premium is not None:
        m &= df.premium_pct >= a.min_premium
    if a.max_outstanding is not None:
        m &= df.outstanding_pct <= a.max_outstanding

    res = df[m].sort_values(a.sort_by)
    cols = ["bond_code", "bond_name", "stock_code", "stock_name", "bond_price",
            "conv_price", "stock_price", "parity", "premium_pct",
            "days_to_maturity", "days_to_put", "outstanding_pct"]
    res = res[cols].round(2)
    print(f"符合 {len(res)} / {len(df)} 檔")
    print(res.to_string(index=False))
    if a.out:
        res.to_csv(a.out, index=False, encoding="utf-8-sig")
        print(f"已輸出 {a.out}", file=sys.stderr)

if __name__ == "__main__":
    main()
