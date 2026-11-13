import json
import os

import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")
SITE = os.path.join(BASE, "site")

CATEGORY_COLORS = {
    "oils": "#2f6f9f",
    "hogs": "#d9772f",
    "eggs": "#3f8f5f",
    "sugar": "#c94f4f",
    "cotton": "#8a6fbf",
    "apple": "#9a6b4f",
    "jujube": "#c45f9f",
    "metals": "#2a9d8f",
    "rubber": "#b7a33a",
    "crude": "#6b7a8f",
    "iron_coal": "#b85c38",
    "gold": "#c9a227",
}

BIG_META = {
    "consumption_price": ("消费指数（主）", "#c94f4f", "solid", True),
    "consumption_full_price": ("消费指数（全成分）", "#e08a8a", "dot", False),
    "industrial_all_price": ("工业指数（主）", "#2f6f9f", "solid", True),
    "industrial_core_price": ("工业指数（核心，不含铂钯）", "#6a9fb5", "dot", False),
    "industrial_all_full_price": ("工业指数（全成分，含铂钯）", "#8a6fbf", "dash", False),
    "consumption_proxy_price": ("消费指数（2005 长历史）", "#c94f4f", "dash", False),
    "industrial_proxy_price": ("工业指数（2005 长历史）", "#2f6f9f", "dash", False),
}


def clean_num(v, digits=3):
    if pd.isna(v):
        return None
    return round(float(v), digits)


def make_series(s, key, name, group, color, dash="solid", visible=True):
    s = s.dropna(subset=["level"]).sort_values("date")
    y = [clean_num(v) for v in s["level"].tolist()]
    x = s["date"].dt.strftime("%Y-%m-%d").tolist()
    latest = y[-1] if y else None
    chg1d = (y[-1] / y[-2] - 1) if len(y) >= 2 else None
    chg1y = (y[-1] / y[-253] - 1) if len(y) >= 253 else None
    return {
        "key": key,
        "name": name,
        "group": group,
        "color": color,
        "dash": dash,
        "visible": visible,
        "x": x,
        "y": y,
        "latest": latest,
        "latestDate": x[-1] if x else None,
        "chg1d": chg1d,
        "chg1y": chg1y,
    }


def subindex_dataset(path, index_map):
    df = pd.read_csv(path, parse_dates=["date"])
    series = []
    for cat, g in df.groupby("category", sort=False):
        name = g["category_name"].iloc[0]
        idx = g["index"].iloc[0]
        group = index_map.get(idx, idx)
        series.append(make_series(g, cat, name, group, CATEGORY_COLORS.get(cat, "#777")))
    order = ["oils", "hogs", "eggs", "sugar", "cotton", "apple", "jujube",
             "metals", "rubber", "crude", "iron_coal", "gold"]
    series.sort(key=lambda s: order.index(s["key"]) if s["key"] in order else 99)
    return series


def ratio_series(df, ind_key, cons_key, key, name, color, dash, visible):
    a = df[df["index"] == ind_key][["date", "level"]].rename(columns={"level": "ind"})
    b = df[df["index"] == cons_key][["date", "level"]].rename(columns={"level": "cons"})
    m = a.merge(b, on="date", how="inner").sort_values("date")
    m["level"] = m["ind"] / m["cons"]
    return make_series(m, key, name, "ratio", color, dash, visible)


def big_dataset():
    main = pd.read_csv(os.path.join(OUT, "index_levels.csv"), parse_dates=["date"])
    proxy = pd.read_csv(os.path.join(OUT, "index_proxy_levels.csv"), parse_dates=["date"])
    df = pd.concat([main, proxy], ignore_index=True)
    series = []
    for key, (name, color, dash, visible) in BIG_META.items():
        g = df[df["index"] == key]
        if len(g) == 0:
            continue
        series.append(make_series(g, key, name, "big", color, dash, visible))
    ratio = [
        ratio_series(main, "industrial_all_price", "consumption_price",
                     "ratio_main", "工业 / 消费（2020 起）", "#6a4c93", "solid", True),
        ratio_series(main, "consumption_price", "industrial_all_price",
                     "ratio_inverse_main", "消费 / 工业（2020 起）", "#d9772f", "solid", True),
        ratio_series(proxy, "industrial_proxy_price", "consumption_proxy_price",
                     "ratio_proxy", "工业 / 消费（2005 起）", "#9b7bbf", "dash", False),
        ratio_series(proxy, "consumption_proxy_price", "industrial_proxy_price",
                     "ratio_inverse_proxy", "消费 / 工业（2005 起）", "#e0a06a", "dash", False),
    ]
    return series, ratio


def main():
    os.makedirs(SITE, exist_ok=True)
    contract = subindex_dataset(os.path.join(OUT, "subindex_levels.csv"),
                                {"consumption": "consumption", "industrial": "industrial"})
    proxy = subindex_dataset(os.path.join(OUT, "subindex_levels_proxy.csv"),
                             {"consumption_proxy": "consumption", "industrial_proxy": "industrial"})
    big, ratio = big_dataset()
    hs = pd.read_csv(os.path.join(BASE, "data", "hs300.csv"), parse_dates=["date"])
    hs["level"] = hs["close"]
    hs300 = make_series(hs, "hs300", "沪深300", "hs300", "#c0392b", "solid", True)
    data = {
        "generatedAt": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M"),
        "big": big,
        "ratio": ratio,
        "hs300": hs300,
        "contract": contract,
        "proxy": proxy,
    }
    path = os.path.join(SITE, "data.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write("window.APP_DATA = ")
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        f.write(";\n")
    print("saved", path, "bytes", os.path.getsize(path))
    print("big", [(s["key"], s["latest"]) for s in big])
    print("ratio", [(s["key"], s["latest"]) for s in ratio])
    print("hs300", hs300["latest"], hs300["latestDate"])
    print("contract", len(contract), "proxy", len(proxy))


if __name__ == "__main__":
    main()
