import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CATEGORIES, INDEXES, PRODUCTS
import build_index
import build_proxy

OUT_DIR = "/home/bl/commodity_index/output"


def product_panels(df, products):
    sub = df[df["product"].isin(products)].copy()
    sub["oi_mult"] = sub["open_interest"] * sub["multiplier"]
    sub["p_oi_mult"] = sub["price"] * sub["oi_mult"]
    num = sub.groupby(["date", "product"])["p_oi_mult"].sum()
    den = sub.groupby(["date", "product"])["oi_mult"].sum()
    P = (num / den).rename("price").unstack("product").reindex(columns=products)
    Gp = sub.groupby(["date", "product"])["mv"].sum().unstack("product").reindex(columns=products)
    master = pd.DatetimeIndex(sorted(sub["date"].unique()), name="date")
    P = P.reindex(master).ffill(limit=5)
    Gp = Gp.reindex(master).ffill(limit=5)
    return P, Gp


def product_index(P):
    first = P.apply(lambda s: s.first_valid_index())
    I = pd.DataFrame(index=P.index, columns=P.columns, dtype=float)
    for col in P.columns:
        base = first[col]
        if base is None:
            continue
        I[col] = P[col] / P.loc[base, col] * 1000.0
    return I


def weighted_average(components, weights):
    w = weights.div(weights.sum(axis=1, min_count=1), axis=0)
    out = (components * w).sum(axis=1, min_count=1)
    out = out.dropna()
    if len(out):
        out = out / out.iloc[0] * 1000.0
    return out


def full_start(panel):
    return panel.dropna().index.min()


def category_dynamic(P, Gp, categories):
    I = product_index(P)
    rows = []
    cat_levels = {}
    for cat, prods in categories.items():
        prods = [p for p in prods if p in P.columns]
        p = P[prods]
        g = Gp[prods]
        i = I[prods]
        level = weighted_average(i, g.shift(1))
        cat_levels[cat] = level
        present = (p.notna() & (p > 0)).sum(axis=1).reindex(level.index)
        cov = present / len(prods)
        gross = g.sum(axis=1, min_count=1).reindex(level.index)
        rows.append(pd.DataFrame({
            "date": level.index, "category": cat,
            "category_name": CATEGORIES[cat]["name"],
            "level": level.values,
            "gross_mv": gross.values,
            "n_products": present.values,
            "coverage": cov.values,
        }))
    return pd.concat(rows, ignore_index=True), pd.DataFrame(cat_levels).sort_index()


def category_full(P, Gp, categories, start):
    I = product_index(P)
    rows = []
    cat_levels = {}
    for cat, prods in categories.items():
        prods = [p for p in prods if p in P.columns]
        p = P[prods]
        g = Gp[prods]
        base = p.loc[start]
        i = p / base * 1000.0
        level = weighted_average(i, g.shift(1))
        level = level[level.index >= start]
        cat_levels[cat] = level
        present = (p.notna() & (p > 0)).sum(axis=1).reindex(level.index)
        cov = present / len(prods)
        gross = g.sum(axis=1, min_count=1).reindex(level.index)
        rows.append(pd.DataFrame({
            "date": level.index, "category": cat,
            "category_name": CATEGORIES[cat]["name"],
            "level": level.values,
            "gross_mv": gross.values,
            "n_products": present.values,
            "coverage": cov.values,
        }))
    return pd.concat(rows, ignore_index=True), pd.DataFrame(cat_levels).sort_index()


def big_from_categories(cat_levels, Gp, categories):
    gk = {}
    for cat, prods in categories.items():
        cols = [p for p in prods if p in Gp.columns]
        gk[cat] = Gp[cols].sum(axis=1, min_count=1)
    Gk = pd.DataFrame(gk).reindex(cat_levels.index)
    level = weighted_average(cat_levels, Gk.shift(1))
    return level, Gk


def write_detail(detail, name):
    detail.to_csv(os.path.join(OUT_DIR, name), index=False, encoding="utf-8-sig")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = build_index.load_contracts()

    cons_cats = {c: CATEGORIES[c]["products"] for c in INDEXES["consumption"]["categories"]}
    ind_cats = {c: CATEGORIES[c]["products"] for c in INDEXES["industrial"]["categories"]}
    cons_prods = [p for c in cons_cats.values() for p in c]
    ind_prods = [p for c in ind_cats.values() for p in c]
    ind_core_prods = [p for p in ind_prods if p not in ("PT", "PD")]

    P_c, Gp_c = product_panels(df, cons_prods)
    P_i, Gp_i = product_panels(df, ind_prods)
    P_i_core, Gp_i_core = product_panels(df, ind_core_prods)

    c_detail, c_levels = category_dynamic(P_c, Gp_c, cons_cats)
    i_detail, i_levels = category_dynamic(P_i, Gp_i, ind_cats)
    c_detail["index"] = "consumption"
    i_detail["index"] = "industrial"
    sub_dynamic = pd.concat([c_detail, i_detail], ignore_index=True)
    write_detail(sub_dynamic, "subindex_levels_price.csv")

    c_full_start = full_start(P_c[cons_prods])
    i_full_start = full_start(P_i[ind_prods])
    i_core_full_start = full_start(P_i_core[ind_core_prods])
    c_full_detail, c_full_levels = category_full(P_c, Gp_c, cons_cats, c_full_start)
    i_full_detail, i_full_levels = category_full(P_i, Gp_i, ind_cats, i_full_start)
    i_core_detail, i_core_levels = category_full(P_i_core, Gp_i_core, ind_cats, i_core_full_start)
    c_full_detail["index"] = "consumption_full"
    i_full_detail["index"] = "industrial_full"
    i_core_detail["index"] = "industrial_core"
    write_detail(pd.concat([c_full_detail, i_full_detail, i_core_detail], ignore_index=True),
                 "subindex_levels_price_full.csv")

    c_big, c_gk = big_from_categories(c_levels, Gp_c, cons_cats)
    i_big, i_gk = big_from_categories(i_levels, Gp_i, ind_cats)
    c_big_full, c_gk_full = big_from_categories(c_full_levels, Gp_c, cons_cats)
    i_big_full, i_gk_full = big_from_categories(i_full_levels, Gp_i, ind_cats)
    i_core_big, i_core_gk = big_from_categories(i_core_levels, Gp_i_core, ind_cats)

    big = pd.concat([
        c_big.rename("level").to_frame().assign(index="consumption_price"),
        c_big_full.rename("level").to_frame().assign(index="consumption_full_price"),
        i_core_big.rename("level").to_frame().assign(index="industrial_core_price"),
        i_big.rename("level").to_frame().assign(index="industrial_all_price"),
        i_big_full.rename("level").to_frame().assign(index="industrial_all_full_price"),
    ]).reset_index().rename(columns={"index": "series"})
    big = big.rename(columns={"series": "index"})
    big.to_csv(os.path.join(OUT_DIR, "index_levels_price.csv"), index=False, encoding="utf-8-sig")

    c_detail.to_csv(os.path.join(OUT_DIR, "subindex_wide_consumption_price.csv"), index=False, encoding="utf-8-sig")
    i_detail.to_csv(os.path.join(OUT_DIR, "subindex_wide_industrial_price.csv"), index=False, encoding="utf-8-sig")

    mdf = build_proxy.load_main()
    Pm_c, Gm_c = product_panels(mdf, cons_prods)
    Pm_i, Gm_i = product_panels(mdf, ind_prods)
    pc_detail, pc_levels = category_dynamic(Pm_c, Gm_c, cons_cats)
    pi_detail, pi_levels = category_dynamic(Pm_i, Gm_i, ind_cats)
    pc_detail["index"] = "consumption_proxy"
    pi_detail["index"] = "industrial_proxy"
    proxy_sub = pd.concat([pc_detail, pi_detail], ignore_index=True)
    write_detail(proxy_sub, "subindex_levels_price_proxy.csv")

    pc_big, _ = big_from_categories(pc_levels, Gm_c, cons_cats)
    pi_big, _ = big_from_categories(pi_levels, Gm_i, ind_cats)
    proxy_big = pd.concat([
        pc_big.rename("level").to_frame().assign(index="consumption_proxy_price"),
        pi_big.rename("level").to_frame().assign(index="industrial_proxy_price"),
    ]).reset_index().rename(columns={"index": "series"})
    proxy_big = proxy_big.rename(columns={"series": "index"})
    proxy_big.to_csv(os.path.join(OUT_DIR, "index_levels_price_proxy.csv"), index=False, encoding="utf-8-sig")

    print("consumption full start", c_full_start.date(), "industrial full start", i_full_start.date(),
          "industrial core start", i_core_full_start.date())
    print("sub rows", len(sub_dynamic), "proxy rows", len(proxy_sub))
    print("\nsub last")
    print(sub_dynamic.groupby(["index", "category"]).tail(1)[
        ["index", "category", "date", "level", "coverage"]].to_string(index=False))
    print("\nbig last")
    print(big.groupby("index").tail(1)[["index", "date", "level"]].to_string(index=False))
    print("\nproxy big last")
    print(proxy_big.groupby("index").tail(1)[["index", "date", "level"]].to_string(index=False))
    print("SAVED", OUT_DIR)


if __name__ == "__main__":
    main()
