"""China commodity index universe and contract metadata.

Multiplier means: contract value = quote price * multiplier.
For products quoted per 500kg or per gram, the multiplier is the number of
quote units in one contract, not the tonnage.
"""

INDEXES = {
    "consumption": {
        "name": "中国消费商品指数",
        "categories": ["oils", "hogs", "eggs", "sugar", "cotton", "apple", "jujube"],
    },
    "industrial": {
        "name": "中国工业商品指数",
        "categories": ["metals", "rubber", "crude", "iron_coal", "gold"],
    },
}

CATEGORIES = {
    "oils": {"name": "油脂", "products": ["Y", "P", "OI", "PK"]},
    "hogs": {"name": "生猪", "products": ["LH"]},
    "eggs": {"name": "鸡蛋", "products": ["JD"]},
    "sugar": {"name": "白糖", "products": ["SR"]},
    "cotton": {"name": "棉花", "products": ["CF"]},
    "apple": {"name": "苹果", "products": ["AP"]},
    "jujube": {"name": "红枣", "products": ["CJ"]},
    "metals": {"name": "金属", "products": ["CU", "AL", "ZN", "PB", "NI", "PT", "PD", "AG"]},
    "rubber": {"name": "橡胶", "products": ["RU"]},
    "crude": {"name": "原油", "products": ["SC"]},
    "iron_coal": {"name": "铁矿石+焦煤", "products": ["I", "JM"]},
    "gold": {"name": "黄金", "products": ["AU"]},
}

PRODUCTS = {
    # ---- consumption ----
    "Y": {"name": "豆油", "exchange": "DCE", "multiplier": 10,
          "months": [1, 3, 5, 7, 8, 9, 11, 12], "main_series": "Y0",
          "start": "2006-01-09"},
    "P": {"name": "棕榈油", "exchange": "DCE", "multiplier": 10,
          "months": list(range(1, 13)), "main_series": "P0",
          "start": "2007-10-29"},
    "OI": {"name": "菜籽油", "exchange": "CZCE", "multiplier": 10,
           "months": [1, 3, 5, 7, 9, 11], "main_series": "OI0",
           "start": "2007-06-08"},
    "PK": {"name": "花生", "exchange": "CZCE", "multiplier": 5,
           "months": [1, 3, 4, 10, 11, 12], "main_series": "PK0",
           "start": "2021-02-01"},
    "LH": {"name": "生猪", "exchange": "DCE", "multiplier": 16,
           "months": [1, 3, 5, 7, 9, 11], "main_series": "LH0",
           "start": "2021-01-08"},
    "JD": {"name": "鸡蛋", "exchange": "DCE", "multiplier": 10,
           "months": list(range(1, 13)), "main_series": "JD0",
           "start": "2013-11-08"},
    "SR": {"name": "白糖", "exchange": "CZCE", "multiplier": 10,
           "months": [1, 3, 5, 7, 9, 11], "main_series": "SR0",
           "start": "2006-01-12"},
    "CF": {"name": "棉花", "exchange": "CZCE", "multiplier": 5,
           "months": [1, 3, 5, 7, 9, 11], "main_series": "CF0",
           "start": "2005-01-04"},
    "AP": {"name": "苹果", "exchange": "CZCE", "multiplier": 10,
           "months": [1, 3, 4, 5, 10, 11, 12], "main_series": "AP0",
           "start": "2017-12-22"},
    "CJ": {"name": "红枣", "exchange": "CZCE", "multiplier": 5,
           "months": [1, 3, 5, 7, 9, 12], "main_series": "CJ0",
           "start": "2019-05-06"},
    # ---- industrial ----
    "CU": {"name": "铜", "exchange": "SHFE", "multiplier": 5,
           "months": list(range(1, 13)), "main_series": "CU0",
           "start": "2005-01-04"},
    "AL": {"name": "铝", "exchange": "SHFE", "multiplier": 5,
           "months": list(range(1, 13)), "main_series": "AL0",
           "start": "2005-01-04"},
    "ZN": {"name": "锌", "exchange": "SHFE", "multiplier": 5,
           "months": list(range(1, 13)), "main_series": "ZN0",
           "start": "2007-03-26"},
    "PB": {"name": "铅", "exchange": "SHFE", "multiplier": 5,
           "months": list(range(1, 13)), "main_series": "PB0",
           "start": "2011-03-24"},
    "NI": {"name": "镍", "exchange": "SHFE", "multiplier": 1,
           "months": list(range(1, 13)), "main_series": "NI0",
           "start": "2015-03-27"},
    "PT": {"name": "铂", "exchange": "GFEX", "multiplier": 1000,
           "months": [2, 4, 6, 8, 10, 12], "main_series": "PT0",
           "start": "2025-11-27"},
    "PD": {"name": "钯", "exchange": "GFEX", "multiplier": 1000,
           "months": [2, 4, 6, 8, 10, 12], "main_series": "PD0",
           "start": "2025-11-27"},
    "AG": {"name": "白银", "exchange": "SHFE", "multiplier": 15,
           "months": list(range(1, 13)), "main_series": "AG0",
           "start": "2012-05-10"},
    "RU": {"name": "天然橡胶", "exchange": "SHFE", "multiplier": 10,
           "months": [1, 3, 4, 5, 6, 7, 8, 9, 10, 11], "main_series": "RU0",
           "start": "2005-01-04"},
    "SC": {"name": "原油", "exchange": "INE", "multiplier": 1000,
           "months": list(range(1, 13)), "main_series": "SC0",
           "start": "2018-03-26"},
    "I": {"name": "铁矿石", "exchange": "DCE", "multiplier": 100,
          "months": list(range(1, 13)), "main_series": "I0",
          "start": "2013-10-18"},
    "JM": {"name": "焦煤", "exchange": "DCE", "multiplier": 60,
           "months": list(range(1, 13)), "main_series": "JM0",
           "start": "2013-03-22"},
    "AU": {"name": "黄金", "exchange": "SHFE", "multiplier": 1000,
           "months": list(range(1, 13)), "main_series": "AU0",
           "start": "2008-01-09"},
}


def product_category(product):
    for key, meta in CATEGORIES.items():
        if product in meta["products"]:
            return key
    raise KeyError(product)
