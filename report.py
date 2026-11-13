import os
import sys

import numpy as np
import pandas as pd

OUT_DIR = "/home/bl/commodity_index/output"


def stats(df):
    df = df.dropna(subset=["ret"]).sort_values("date")
    if len(df) < 2:
        return {}
    r = df["ret"].astype(float)
    level = df["level"].astype(float)
    n = len(r)
    years = n / 252.0
    cagr = (level.iloc[-1] / level.iloc[0]) ** (1 / years) - 1 if years > 0 else np.nan
    vol = r.std(ddof=1) * np.sqrt(252)
    sharpe = r.mean() / r.std(ddof=1) * np.sqrt(252) if r.std(ddof=1) > 0 else np.nan
    dd = (level / level.cummax() - 1).min()
    return {
        "start": df["date"].min().date(),
        "end": df["date"].max().date(),
        "days": n,
        "cagr": cagr,
        "vol": vol,
        "sharpe": sharpe,
        "max_dd": dd,
        "worst_day": r.min(),
        "best_day": r.max(),
        "coverage_end": df["coverage_products"].iloc[-1],
    }


def main():
    levels = pd.read_csv(os.path.join(OUT_DIR, "index_levels.csv"), parse_dates=["date"])
    proxy = pd.read_csv(os.path.join(OUT_DIR, "index_proxy_levels.csv"), parse_dates=["date"])
    catw = pd.read_csv(os.path.join(OUT_DIR, "weights_category.csv"), parse_dates=["date"])
    prodw = pd.read_csv(os.path.join(OUT_DIR, "weights_product.csv"), parse_dates=["date"])

    all_levels = pd.concat([levels, proxy], ignore_index=True)
    rows = []
    for name, g in all_levels.groupby("index"):
        s = stats(g)
        s["index"] = name
        rows.append(s)
    summary = pd.DataFrame(rows).set_index("index")
    cols = ["start", "end", "days", "cagr", "vol", "sharpe", "max_dd", "worst_day", "best_day", "coverage_end"]
    summary = summary[cols].sort_values("start")
    summary.to_csv(os.path.join(OUT_DIR, "summary.csv"), encoding="utf-8-sig")
    print("=== SUMMARY ===")
    print(summary.to_string(float_format=lambda x: f"{x:.4f}"))

    print("\n=== CORRELATION (overlapping daily returns) ===")
    pivot = all_levels.pivot_table(index="date", columns="index", values="ret")
    print(pivot.corr().round(3).to_string())

    print("\n=== WEIGHT SUM CHECK ===")
    cs = catw.groupby(["date", "index"])["weight"].sum().groupby("index").agg(["min", "max", "count"])
    print(cs.to_string(float_format=lambda x: f"{x:.6f}"))
    ps = prodw.dropna(subset=["w_in_index"]).groupby(["date", "index"])["w_in_index"].sum().groupby("index").agg(["min", "max", "count"])
    print(ps.to_string(float_format=lambda x: f"{x:.6f}"))

    print("\n=== LATEST CATEGORY WEIGHTS ===")
    for name, date in catw.groupby("index")["date"].max().items():
        g = catw[(catw["index"] == name) & (catw["date"] == date)]
        print("\n", name, date.date())
        print(g[["category", "weight", "gross_mv"]].sort_values("weight", ascending=False).to_string(index=False))

    print("\n=== LATEST TOP PRODUCT WEIGHTS ===")
    for name, date in prodw.groupby("index")["date"].max().items():
        g = prodw[(prodw["index"] == name) & (prodw["date"] == date)]
        print("\n", name, date.date())
        print(g.sort_values("w_in_index", ascending=False).head(15)[
            ["category", "product", "w_in_category", "w_in_index", "gross_mv"]
        ].to_string(index=False))


if __name__ == "__main__":
    main()
