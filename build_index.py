import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CATEGORIES, INDEXES, PRODUCTS

DATA_DIR = "/home/bl/commodity_index/data"
OUT_DIR = "/home/bl/commodity_index/output"
CONTRACT_PATH = os.path.join(DATA_DIR, "contracts_2020_2027.parquet")


def load_contracts(path=CONTRACT_PATH, min_date="2020-01-01"):
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
    df = df.sort_values(["symbol", "date"])
    df["ret"] = df.groupby("symbol")["price"].pct_change()
    df["w_in_product"] = df["mv"] / df.groupby(["date", "product"])["mv"].transform("sum")
    df["w_prev"] = df.groupby("symbol")["w_in_product"].shift(1)
    if min_date:
        df = df[df["date"] >= min_date].copy()
    return df


def product_panels(df, products):
    sub = df[df["product"].isin(products)].copy()
    Gp = sub.groupby(["date", "product"])["mv"].sum().unstack("product").sort_index()
    Gp = Gp.reindex(columns=products)

    c = sub.dropna(subset=["ret", "w_prev"]).copy()
    c = c[c["w_prev"] > 0]
    c["wr"] = c["w_prev"] * c["ret"]
    num = c.groupby(["date", "product"])["wr"].sum()
    den = c.groupby(["date", "product"])["w_prev"].sum()
    pr = (num / den).rename("ret").unstack("product").reindex(columns=products)

    master = pd.DatetimeIndex(sorted(sub["date"].unique()), name="date")
    Gp = Gp.reindex(master).ffill(limit=5)
    pr = pr.reindex(master)
    pr = pr.where(Gp.notna()).fillna(0.0)
    return Gp, pr


def category_panels(Gp, pr, categories):
    Gk = {}
    Kr = {}
    Wp = {}
    for cat, prods in categories.items():
        prods = [p for p in prods if p in Gp.columns]
        g = Gp[prods]
        gk = g.sum(axis=1, min_count=1)
        Gk[cat] = gk
        gk_prev = gk.shift(1)
        w = g.shift(1).div(gk_prev, axis=0)
        wl = w.stack().rename("w").reset_index()
        rl = pr[prods].stack().rename("ret").reset_index()
        m = wl.merge(rl, on=["date", "product"], how="inner").dropna(subset=["w", "ret"])
        m = m[m["w"] > 0]
        num = (m["w"] * m["ret"]).groupby(m["date"]).sum()
        den = m["w"].groupby(m["date"]).sum()
        Kr[cat] = (num / den).rename(cat)
        Wp[cat] = w
    Gk = pd.DataFrame(Gk).sort_index()
    Kr = pd.DataFrame(Kr).sort_index()
    return Gk, Kr, Wp


def big_index(Gk, Kr):
    gk_prev = Gk.shift(1)
    total_prev = gk_prev.sum(axis=1, min_count=1)
    w = gk_prev.div(total_prev, axis=0)
    wl = w.stack().rename("w").reset_index().rename(columns={"level_1": "category"})
    rl = Kr.stack().rename("ret").reset_index().rename(columns={"level_1": "category"})
    m = wl.merge(rl, on=["date", "category"], how="inner").dropna(subset=["w", "ret"])
    m = m[m["w"] > 0]
    num = (m["w"] * m["ret"]).groupby(m["date"]).sum()
    den = m["w"].groupby(m["date"]).sum()
    ret = (num / den).rename("ret")
    return ret, w, total_prev


def level_from_ret(ret, base=1000.0):
    ret = ret.dropna().sort_index()
    if len(ret) == 0:
        return pd.Series(dtype=float)
    adj = ret.copy()
    adj.iloc[0] = 0.0
    return base * (1.0 + adj).cumprod()


def run_index(df, name, products, categories, start=None):
    Gp, pr = product_panels(df, products)
    Gk, Kr, Wp = category_panels(Gp, pr, categories)
    ret, Wk, total_prev = big_index(Gk, Kr)
    if start is not None:
        ret = ret[ret.index >= start]
    level = level_from_ret(ret)
    present = (Gp[products].notna() & (Gp[products] > 0)).sum(axis=1)
    cov = (present / len(products)).reindex(level.index)
    ncat = (Gk[categories.keys()].notna() & (Gk[categories.keys()] > 0)).sum(axis=1)
    cat_cov = (ncat / len(categories)).reindex(level.index)

    levels = pd.DataFrame({
        "date": level.index,
        "index": name,
        "level": level.values,
        "ret": ret.reindex(level.index).values,
        "coverage_products": cov.values,
        "coverage_categories": cat_cov.values,
    })

    cat_w = Wk.stack().rename("weight").reset_index().rename(columns={"level_1": "category"})
    cat_w["index"] = name
    cat_w = cat_w.merge(
        Gk.stack().rename("gross_mv").reset_index().rename(columns={"level_1": "category"}),
        on=["date", "category"], how="left",
    )

    prod_rows = []
    for cat, prods in categories.items():
        prods = [p for p in prods if p in Gp.columns]
        g = Gp[prods]
        gk_prev = g.sum(axis=1, min_count=1).shift(1)
        w_in_cat = g.shift(1).div(gk_prev, axis=0)
        total = Wk[cat] if cat in Wk.columns else pd.Series(index=Gp.index, dtype=float)
        for p in prods:
            prod_rows.append(pd.DataFrame({
                "date": Gp.index,
                "index": name,
                "category": cat,
                "product": p,
                "gross_mv": g[p].values,
                "w_in_category": w_in_cat[p].values,
                "w_in_index": (w_in_cat[p] * total).values,
            }))
    prod_w = pd.concat(prod_rows, ignore_index=True) if prod_rows else pd.DataFrame()

    return levels, cat_w, prod_w, Gp, pr, Gk, Kr


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_contracts()

    consumption_products = [p for c in INDEXES["consumption"]["categories"] for p in CATEGORIES[c]["products"]]
    industrial_products = [p for c in INDEXES["industrial"]["categories"] for p in CATEGORIES[c]["products"]]
    industrial_core_products = [p for p in industrial_products if p not in ("PT", "PD")]

    consumption_cats = {c: CATEGORIES[c]["products"] for c in INDEXES["consumption"]["categories"]}
    industrial_cats = {c: CATEGORIES[c]["products"] for c in INDEXES["industrial"]["categories"]}

    all_levels = []
    all_cat_w = []
    all_prod_w = []

    specs = [
        ("consumption_dynamic", consumption_products, consumption_cats, "2020-01-02"),
        ("consumption_full", consumption_products, consumption_cats, "2021-02-01"),
        ("industrial_core", industrial_core_products, industrial_cats, "2020-01-02"),
        ("industrial_all_dynamic", industrial_products, industrial_cats, "2020-01-02"),
        ("industrial_all_full", industrial_products, industrial_cats, "2025-11-27"),
    ]
    for name, products, cats, start in specs:
        levels, cat_w, prod_w, Gp, pr, Gk, Kr = run_index(df, name, products, cats, start)
        all_levels.append(levels)
        all_cat_w.append(cat_w)
        all_prod_w.append(prod_w)
        print(name, "start", levels["date"].min(), "end", levels["date"].max(),
              "rows", len(levels), "coverage_end", levels["coverage_products"].iloc[-1])

        levels.to_csv(os.path.join(OUT_DIR, f"index_{name}.csv"), index=False, encoding="utf-8-sig")
        cat_w.to_csv(os.path.join(OUT_DIR, f"weights_category_{name}.csv"), index=False, encoding="utf-8-sig")
        prod_w.to_csv(os.path.join(OUT_DIR, f"weights_product_{name}.csv"), index=False, encoding="utf-8-sig")
        Kr.to_csv(os.path.join(OUT_DIR, f"category_returns_{name}.csv"), encoding="utf-8-sig")

    pd.concat(all_levels, ignore_index=True).to_csv(
        os.path.join(OUT_DIR, "index_levels.csv"), index=False, encoding="utf-8-sig")
    pd.concat(all_cat_w, ignore_index=True).to_csv(
        os.path.join(OUT_DIR, "weights_category.csv"), index=False, encoding="utf-8-sig")
    pd.concat(all_prod_w, ignore_index=True).to_csv(
        os.path.join(OUT_DIR, "weights_product.csv"), index=False, encoding="utf-8-sig")
    print("SAVED", OUT_DIR)


if __name__ == "__main__":
    main()
