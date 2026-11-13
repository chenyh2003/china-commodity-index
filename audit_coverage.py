import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CATEGORIES, INDEXES, PRODUCTS

DATA_DIR = "/home/bl/commodity_index/data"
CONTRACT_PATH = os.path.join(DATA_DIR, "contracts_2020_2027.parquet")


def load_contracts(path=CONTRACT_PATH):
    df = pd.read_parquet(path)
    df["date"] = pd.to_datetime(df["date"])
    df["multiplier"] = df["product"].map(lambda p: PRODUCTS[p]["multiplier"])
    df["exchange"] = df["product"].map(lambda p: PRODUCTS[p]["exchange"])
    df["price"] = df["settle"].where(df["settle"] > 0, df["close"])
    df = df[(df["price"] > 0) & (df["open_interest"] > 0)].copy()
    ym = df["date"].dt.year * 100 + df["date"].dt.month
    delivery_ym = df["contract_year"] * 100 + df["contract_month"]
    df = df[ym < delivery_ym].copy()
    df["mv"] = df["price"] * df["open_interest"] * df["multiplier"]
    return df


def main():
    df = load_contracts()
    print("rows", len(df), "dates", df["date"].min().date(), df["date"].max().date())
    print("products", df["product"].nunique())

    print("\n=== product coverage by year ===")
    df["year"] = df["date"].dt.year
    g = df.groupby(["product", "year"]).agg(
        days=("date", "nunique"),
        contracts=("symbol", "nunique"),
        oi=("open_interest", "sum"),
        mv=("mv", "sum"),
    ).reset_index()
    print(g.pivot(index="product", columns="year", values="days").fillna(0).astype(int).to_string())

    print("\n=== product first/last active date ===")
    g2 = df.groupby("product").agg(
        first=("date", "min"), last=("date", "max"),
        days=("date", "nunique"), contracts=("symbol", "nunique"),
    ).sort_values("first")
    print(g2.to_string())

    print("\n=== category product presence ===")
    dates = pd.DatetimeIndex(sorted(df["date"].unique()))
    for cat, meta in CATEGORIES.items():
        prods = meta["products"]
        panel = df[df["product"].isin(prods)].groupby("date")["product"].nunique().reindex(dates, fill_value=0)
        full_dates = panel[panel == len(prods)].index
        print(f"{cat:10s} products={len(prods)} first_any={panel[panel > 0].index.min()} "
              f"first_full={full_dates.min() if len(full_dates) else None}")

    print("\n=== index coverage ===")
    for idx, meta in INDEXES.items():
        prods = [p for c in meta["categories"] for p in CATEGORIES[c]["products"]]
        panel = df[df["product"].isin(prods)].groupby("date")["product"].nunique().reindex(dates, fill_value=0)
        full_dates = panel[panel == len(prods)].index
        print(f"{idx:12s} products={len(prods)} first_any={panel[panel > 0].index.min()} "
              f"first_full={full_dates.min() if len(full_dates) else None}")

    print("\n=== contracts per product per date (latest 10 dates) ===")
    last = df[df["date"].isin(sorted(df["date"].unique())[-10:])]
    print(last.groupby(["date", "product"])["symbol"].nunique().unstack("product").to_string())


if __name__ == "__main__":
    main()
