import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CATEGORIES, INDEXES, PRODUCTS

DATA_DIR = "/home/bl/commodity_index/data"
OUT_DIR = "/home/bl/commodity_index/output"
MAIN_PATH = os.path.join(DATA_DIR, "main_sina.parquet")


def load_main():
    df = pd.read_parquet(MAIN_PATH)
    df["date"] = pd.to_datetime(df["date"])
    series_to_product = {v["main_series"]: k for k, v in PRODUCTS.items()}
    df = df[df["series_id"].isin(series_to_product)].copy()
    df["product"] = df["series_id"].map(series_to_product)
    df["multiplier"] = df["product"].map(lambda p: PRODUCTS[p]["multiplier"])
    df["price"] = df["close"]
    df = df[(df["price"] > 0) & (df["open_interest"] > 0)].copy()
    df["mv"] = df["price"] * df["open_interest"] * df["multiplier"]
    df = df.sort_values(["product", "date"])
    med = df.groupby("product")["mv"].transform(
        lambda s: s.rolling(21, min_periods=5).median().shift(1))
    df = df[med.isna() | (df["mv"] >= 0.10 * med)].copy()
    return df


def panels(df, products):
    sub = df[df["product"].isin(products)]
    Gp = sub.pivot_table(
        index="date", columns="product", values="mv", aggfunc="last").reindex(columns=products)
    P = sub.pivot_table(
        index="date", columns="product", values="price", aggfunc="last").reindex(columns=products)
    master = pd.DatetimeIndex(sorted(sub["date"].unique()), name="date")
    Gp = Gp.reindex(master).ffill(limit=5)
    P = P.reindex(master).ffill(limit=5)
    pr = P.pct_change(fill_method=None)
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
        w = g.shift(1).div(gk.shift(1), axis=0)
        wl = w.stack().rename("w").reset_index()
        rl = pr[prods].stack().rename("ret").reset_index()
        m = wl.merge(rl, on=["date", "product"], how="inner").dropna(subset=["w", "ret"])
        m = m[m["w"] > 0]
        num = (m["w"] * m["ret"]).groupby(m["date"]).sum()
        den = m["w"].groupby(m["date"]).sum()
        Kr[cat] = (num / den).rename(cat)
        Wp[cat] = w
    return pd.DataFrame(Gk).sort_index(), pd.DataFrame(Kr).sort_index(), Wp


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
    return (num / den).rename("ret"), w, total_prev


def level_from_ret(ret, base=1000.0):
    ret = ret.dropna().sort_index()
    if len(ret) == 0:
        return pd.Series(dtype=float)
    adj = ret.copy()
    adj.iloc[0] = 0.0
    return base * (1.0 + adj).cumprod()


def run(df, name, products, categories):
    Gp, pr = panels(df, products)
    Gk, Kr, Wp = category_panels(Gp, pr, categories)
    ret, Wk, total_prev = big_index(Gk, Kr)
    level = level_from_ret(ret)
    present = (Gp[products].notna() & (Gp[products] > 0)).sum(axis=1)
    cov = (present / len(products)).reindex(level.index)
    ncat = (Gk[categories.keys()].notna() & (Gk[categories.keys()] > 0)).sum(axis=1)
    cat_cov = (ncat / len(categories)).reindex(level.index)
    levels = pd.DataFrame({
        "date": level.index, "index": name, "level": level.values,
        "ret": ret.reindex(level.index).values,
        "coverage_products": cov.values, "coverage_categories": cat_cov.values,
    })
    cat_w = Wk.stack().rename("weight").reset_index().rename(columns={"level_1": "category"})
    cat_w["index"] = name
    cat_w = cat_w.merge(
        Gk.stack().rename("gross_mv").reset_index().rename(columns={"level_1": "category"}),
        on=["date", "category"], how="left")
    prod_rows = []
    for cat, prods in categories.items():
        prods = [p for p in prods if p in Gp.columns]
        g = Gp[prods]
        w_in_cat = g.shift(1).div(g.sum(axis=1, min_count=1).shift(1), axis=0)
        total = Wk[cat] if cat in Wk.columns else pd.Series(index=Gp.index, dtype=float)
        for p in prods:
            prod_rows.append(pd.DataFrame({
                "date": Gp.index, "index": name, "category": cat, "product": p,
                "gross_mv": g[p].values, "w_in_category": w_in_cat[p].values,
                "w_in_index": (w_in_cat[p] * total).values,
            }))
    return levels, cat_w, pd.concat(prod_rows, ignore_index=True), Kr


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = load_main()
    specs = [
        ("consumption_proxy", [p for c in INDEXES["consumption"]["categories"] for p in CATEGORIES[c]["products"]],
         {c: CATEGORIES[c]["products"] for c in INDEXES["consumption"]["categories"]}),
        ("industrial_proxy", [p for c in INDEXES["industrial"]["categories"] for p in CATEGORIES[c]["products"]],
         {c: CATEGORIES[c]["products"] for c in INDEXES["industrial"]["categories"]}),
    ]
    all_levels, all_cat_w, all_prod_w = [], [], []
    for name, products, cats in specs:
        levels, cat_w, prod_w, Kr = run(df, name, products, cats)
        all_levels.append(levels)
        all_cat_w.append(cat_w)
        all_prod_w.append(prod_w)
        print(name, "start", levels["date"].min(), "end", levels["date"].max(),
              "rows", len(levels), "coverage_end", levels["coverage_products"].iloc[-1])
        print("  big daily ret abs>10%:", int((levels["ret"].abs() > 0.10).sum()))
        levels.to_csv(os.path.join(OUT_DIR, f"index_{name}.csv"), index=False, encoding="utf-8-sig")
        cat_w.to_csv(os.path.join(OUT_DIR, f"weights_category_{name}.csv"), index=False, encoding="utf-8-sig")
        prod_w.to_csv(os.path.join(OUT_DIR, f"weights_product_{name}.csv"), index=False, encoding="utf-8-sig")
    pd.concat(all_levels, ignore_index=True).to_csv(
        os.path.join(OUT_DIR, "index_proxy_levels.csv"), index=False, encoding="utf-8-sig")
    pd.concat(all_cat_w, ignore_index=True).to_csv(
        os.path.join(OUT_DIR, "weights_category_proxy.csv"), index=False, encoding="utf-8-sig")
    pd.concat(all_prod_w, ignore_index=True).to_csv(
        os.path.join(OUT_DIR, "weights_product_proxy.csv"), index=False, encoding="utf-8-sig")
    print("SAVED", OUT_DIR)


if __name__ == "__main__":
    main()
