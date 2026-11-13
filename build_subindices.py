import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import CATEGORIES, INDEXES
import build_index
import build_proxy

OUT_DIR = "/home/bl/commodity_index/output"


def make_subindices(Gp, pr, categories, index_name, source):
    Gk, Kr, Wp = build_index.category_panels(Gp, pr, categories)
    rows = []
    wide = {}
    for cat, prods in categories.items():
        prods = [p for p in prods if p in Gp.columns]
        ret = Kr[cat].dropna().sort_index()
        if len(ret) == 0:
            continue
        level = build_index.level_from_ret(ret)
        gross = Gk[cat].reindex(level.index)
        present = (Gp[prods].notna() & (Gp[prods] > 0)).sum(axis=1).reindex(level.index)
        cov = present / len(prods)
        out = pd.DataFrame({
            "date": level.index,
            "index": index_name,
            "category": cat,
            "category_name": CATEGORIES[cat]["name"],
            "source": source,
            "level": level.values,
            "ret": ret.reindex(level.index).values,
            "gross_mv": gross.values,
            "n_products": present.values,
            "coverage": cov.values,
        })
        rows.append(out)
        wide[cat] = level
    detail = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    wide = pd.DataFrame(wide).sort_index()
    return detail, wide


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    df = build_index.load_contracts()
    cons_cats = {c: CATEGORIES[c]["products"] for c in INDEXES["consumption"]["categories"]}
    ind_cats = {c: CATEGORIES[c]["products"] for c in INDEXES["industrial"]["categories"]}

    cons_prods = [p for c in cons_cats.values() for p in c]
    ind_prods = [p for c in ind_cats.values() for p in c]

    Gp1, pr1 = build_index.product_panels(df, cons_prods)
    d1, w1 = make_subindices(Gp1, pr1, cons_cats, "consumption", "contract")
    Gp2, pr2 = build_index.product_panels(df, ind_prods)
    d2, w2 = make_subindices(Gp2, pr2, ind_cats, "industrial", "contract")

    main_detail = pd.concat([d1, d2], ignore_index=True)
    main_detail.to_csv(os.path.join(OUT_DIR, "subindex_levels.csv"), index=False, encoding="utf-8-sig")
    w1.to_csv(os.path.join(OUT_DIR, "subindex_wide_consumption.csv"), encoding="utf-8-sig")
    w2.to_csv(os.path.join(OUT_DIR, "subindex_wide_industrial.csv"), encoding="utf-8-sig")

    mdf = build_proxy.load_main()
    Gp3, pr3 = build_proxy.panels(mdf, cons_prods)
    d3, w3 = make_subindices(Gp3, pr3, cons_cats, "consumption_proxy", "main")
    Gp4, pr4 = build_proxy.panels(mdf, ind_prods)
    d4, w4 = make_subindices(Gp4, pr4, ind_cats, "industrial_proxy", "main")

    proxy_detail = pd.concat([d3, d4], ignore_index=True)
    proxy_detail.to_csv(os.path.join(OUT_DIR, "subindex_levels_proxy.csv"), index=False, encoding="utf-8-sig")
    w3.to_csv(os.path.join(OUT_DIR, "subindex_wide_consumption_proxy.csv"), encoding="utf-8-sig")
    w4.to_csv(os.path.join(OUT_DIR, "subindex_wide_industrial_proxy.csv"), encoding="utf-8-sig")

    print("contract rows", len(main_detail), "proxy rows", len(proxy_detail))
    for name, g in main_detail.groupby("category"):
        print(name, g["date"].min(), g["date"].max(), len(g), g["level"].iloc[-1])
    print("SAVED", OUT_DIR)


if __name__ == "__main__":
    main()
