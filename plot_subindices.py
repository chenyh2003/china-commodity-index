import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "output")

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["figure.dpi"] = 140

C_CONSUMPTION = ["oils", "hogs", "eggs", "sugar", "cotton", "apple", "jujube"]
C_INDUSTRIAL = ["metals", "rubber", "crude", "iron_coal", "gold"]


def load_detail(path):
    df = pd.read_csv(path, parse_dates=["date"])
    df["category_name"] = df["category_name"].astype(str)
    return df


def line_panel(ax, pivot, title, log=False):
    colors = plt.get_cmap("tab10").colors
    for i, col in enumerate(pivot.columns):
        s = pivot[col].dropna()
        ax.plot(s.index, s.values, label=col, linewidth=1.4, color=colors[i % len(colors)])
    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.axhline(1000, color="grey", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.grid(alpha=0.25)
    if log:
        ax.set_yscale("log")
    ax.legend(loc="upper left", fontsize=8, ncol=2, frameon=False)
    ax.set_ylabel("指数（起点=1000）" if not log else "指数（对数轴，起点=1000）")


def plot_overview():
    detail = load_detail(os.path.join(OUT, "subindex_levels.csv"))
    fig, axes = plt.subplots(2, 1, figsize=(15, 11), sharex=False)
    for ax, idx, cats, title in [
        (axes[0], "consumption", C_CONSUMPTION, "中国消费商品：小指数（2020 起，持仓加权平均价格）"),
        (axes[1], "industrial", C_INDUSTRIAL, "中国工业商品：小指数（2020 起，持仓加权平均价格）"),
    ]:
        sub = detail[(detail["index"] == idx) & (detail["category"].isin(cats))]
        pivot = sub.pivot(index="date", columns="category_name", values="level")
        order = [sub[sub["category"] == c]["category_name"].iloc[0] for c in cats if c in set(sub["category"])]
        pivot = pivot[[c for c in order if c in pivot.columns]]
        line_panel(ax, pivot, title)
    fig.tight_layout()
    path = os.path.join(OUT, "总图_小指数_2020.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(path)


def plot_proxy_overview():
    detail = load_detail(os.path.join(OUT, "subindex_levels_proxy.csv"))
    fig, axes = plt.subplots(2, 1, figsize=(15, 11), sharex=False)
    for ax, idx, cats, title in [
        (axes[0], "consumption_proxy", C_CONSUMPTION, "中国消费商品：小指数长历史代理（2005 起，主力连续）"),
        (axes[1], "industrial_proxy", C_INDUSTRIAL, "中国工业商品：小指数长历史代理（2005 起，主力连续）"),
    ]:
        sub = detail[(detail["index"] == idx) & (detail["category"].isin(cats))]
        pivot = sub.pivot(index="date", columns="category_name", values="level")
        order = [sub[sub["category"] == c]["category_name"].iloc[0] for c in cats if c in set(sub["category"])]
        pivot = pivot[[c for c in order if c in pivot.columns]]
        line_panel(ax, pivot, title, log=True)
    fig.tight_layout()
    path = os.path.join(OUT, "总图_小指数_2005.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(path)


def plot_facets():
    detail = load_detail(os.path.join(OUT, "subindex_levels.csv"))
    cats = C_CONSUMPTION + C_INDUSTRIAL
    fig, axes = plt.subplots(3, 4, figsize=(20, 12))
    axes = axes.ravel()
    for ax, cat in zip(axes, cats):
        sub = detail[detail["category"] == cat]
        name = sub["category_name"].iloc[0]
        s = sub.set_index("date")["level"].dropna()
        ax.plot(s.index, s.values, color="#2f6f9f", linewidth=1.4)
        ax.axhline(1000, color="grey", linewidth=0.8, linestyle="--", alpha=0.6)
        ax.set_title(f"{name}（最新 {s.iloc[-1]:.0f}）", fontsize=11, fontweight="bold")
        ax.grid(alpha=0.25)
        ax.tick_params(axis="x", labelsize=8, rotation=30)
        ax.tick_params(axis="y", labelsize=8)
    for ax in axes[len(cats):]:
        ax.axis("off")
    fig.suptitle("中国商品：12 个小指数分面（2020 起，持仓加权平均价格）", fontsize=16, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    path = os.path.join(OUT, "分面_小指数_2020.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(path)



def plot_all_overlay():
    detail = load_detail(os.path.join(OUT, "subindex_levels.csv"))
    pivot = detail.pivot(index="date", columns="category_name", values="level")
    fig, ax = plt.subplots(figsize=(16, 8))
    colors = plt.get_cmap("tab20").colors
    for i, col in enumerate(pivot.columns):
        s = pivot[col].dropna()
        ax.plot(s.index, s.values, label=col, linewidth=1.3, color=colors[i % len(colors)])
    ax.set_title("中国商品：12 个小指数总图（2020 起，持仓加权平均价格，起点=1000）", fontsize=14, fontweight="bold")
    ax.axhline(1000, color="grey", linewidth=0.8, linestyle="--", alpha=0.6)
    ax.grid(alpha=0.25)
    ax.legend(loc="upper left", fontsize=8, ncol=3, frameon=False)
    ax.set_ylabel("指数（起点=1000）")
    fig.tight_layout()
    path = os.path.join(OUT, "总图_小指数_全叠加.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(path)


def ratio_frame(df, num_key, den_key):
    a = df[df["index"] == num_key].set_index("date")["level"]
    b = df[df["index"] == den_key].set_index("date")["level"]
    return (a / b).dropna()


def plot_ratio():
    main = pd.read_csv(os.path.join(OUT, "index_levels.csv"), parse_dates=["date"])
    proxy = pd.read_csv(os.path.join(OUT, "index_proxy_levels.csv"), parse_dates=["date"])
    hs = pd.read_csv(os.path.join(BASE, "data", "hs300.csv"), parse_dates=["date"])
    fig, axes = plt.subplots(3, 1, figsize=(15, 13), sharex=False)
    specs = [
        (axes[0], "industrial_all_price", "consumption_price",
         "industrial_proxy_price", "consumption_proxy_price", "工业 / 消费"),
        (axes[1], "consumption_price", "industrial_all_price",
         "consumption_proxy_price", "industrial_proxy_price", "消费 / 工业"),
    ]
    for ax, num, den, pnum, pden, title in specs:
        r_main = ratio_frame(main, num, den)
        r_proxy = ratio_frame(proxy, pnum, pden)
        ax.plot(r_proxy.index, r_proxy.values, color="#9b7bbf", linewidth=1.3,
                linestyle="--", label="2005 起（主力连续代理）")
        ax.plot(r_main.index, r_main.values, color="#6a4c93", linewidth=1.6,
                label="2020 起（逐合约）")
        ax.axhline(1.0, color="grey", linewidth=0.8, linestyle="--", alpha=0.6)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=9, frameon=False)
        ax.set_ylabel("比值")
    axes[2].plot(hs["date"], hs["close"], color="#c0392b", linewidth=1.4)
    axes[2].set_title("沪深300", fontsize=13, fontweight="bold")
    axes[2].grid(alpha=0.25)
    axes[2].set_ylabel("点")
    fig.tight_layout()
    path = os.path.join(OUT, "总图_比值曲线.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(path)


def plot_big():
    main = pd.read_csv(os.path.join(OUT, "index_levels.csv"), parse_dates=["date"])
    proxy = pd.read_csv(os.path.join(OUT, "index_proxy_levels.csv"), parse_dates=["date"])
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for ax, group, title in [
        (axes[0], ["consumption_price", "consumption_full_price", "consumption_proxy_price"], "消费商品指数"),
        (axes[1], ["industrial_core_price", "industrial_all_price", "industrial_all_full_price", "industrial_proxy_price"], "工业商品指数"),
    ]:
        for name in group:
            df = main if name in set(main["index"]) else proxy
            s = df[df["index"] == name].set_index("date")["level"].dropna()
            ax.plot(s.index, s.values, label=name, linewidth=1.5)
        ax.set_title(title, fontsize=13, fontweight="bold")
        ax.grid(alpha=0.25)
        ax.legend(fontsize=8, frameon=False)
        ax.set_ylabel("指数（起点=1000）")
    fig.tight_layout()
    path = os.path.join(OUT, "总图_大指数.png")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    plot_overview()
    plot_proxy_overview()
    plot_facets()
    plot_all_overlay()
    plot_ratio()
    plot_big()

