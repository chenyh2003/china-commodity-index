import os
import sys
import time
import traceback

import akshare as ak
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import PRODUCTS

OUT_DIR = "/home/bl/commodity_index/data"
START_YEAR = 2020
END_YEAR = 2027
SLEEP = 0.05


def contract_symbol(code, year, month):
    return f"{code}{year % 100:02d}{month:02d}"


def fetch(symbol, retries=3):
    last = None
    for attempt in range(retries):
        try:
            df = ak.futures_zh_daily_sina(symbol=symbol)
            if df is None or len(df) == 0:
                return None
            df = df.rename(columns={"hold": "open_interest"})
            df["symbol"] = symbol
            df["source"] = "sina"
            return df
        except Exception as exc:
            last = exc
            time.sleep(0.8 * (attempt + 1))
    if last is not None:
        print("FAIL", symbol, repr(last))
    return None


def download_contracts():
    frames = []
    meta_rows = []
    total = 0
    for code, product in PRODUCTS.items():
        start_year = max(START_YEAR, int(product["start"][:4]))
        for year in range(start_year, END_YEAR + 1):
            for month in product["months"]:
                symbol = contract_symbol(code, year, month)
                df = fetch(symbol)
                total += 1
                if df is None or len(df) == 0:
                    continue
                df["product"] = code
                frames.append(df)
                meta_rows.append({
                    "symbol": symbol,
                    "product": code,
                    "exchange": product["exchange"],
                    "rows": len(df),
                    "start": df["date"].min(),
                    "end": df["date"].max(),
                })
                print("OK", symbol, len(df), df["date"].min(), df["date"].max(), flush=True)
                time.sleep(SLEEP)
        print("DONE_PRODUCT", code, "requests", total, flush=True)

    if not frames:
        raise RuntimeError("no contract data downloaded")

    out = pd.concat(frames, ignore_index=True)
    out["date"] = pd.to_datetime(out["date"]).dt.strftime("%Y-%m-%d")
    out["contract_year"] = 2000 + out["symbol"].str.extract(r"^[A-Za-z]+(\d{2})\d{2}$")[0].astype(int)
    out["contract_month"] = out["symbol"].str.extract(r"^[A-Za-z]+\d{2}(\d{2})$")[0].astype(int)
    for col in ["open", "high", "low", "close", "volume", "open_interest", "settle"]:
        out[col] = pd.to_numeric(out[col], errors="coerce")
    out = out.drop_duplicates(["date", "symbol"]).sort_values(["symbol", "date"])

    contract_path = os.path.join(OUT_DIR, "contracts_2020_2027.parquet")
    meta_path = os.path.join(OUT_DIR, "contracts_2020_2027_meta.csv")
    out.to_parquet(contract_path, index=False)
    pd.DataFrame(meta_rows).to_csv(meta_path, index=False, encoding="utf-8-sig")
    print("SAVED", contract_path, len(out), flush=True)
    print("SAVED", meta_path, len(meta_rows), flush=True)


def download_main():
    sys.path.insert(0, "/data/bl/data_raw/ops")
    from warehouse import Warehouse

    w = Warehouse()
    df = w.get("futures_main_sina", limit=None)
    df.columns = [
        "date", "series_id", "vintage_date", "series_title", "frequency",
        "open", "high", "low", "close", "volume", "open_interest",
        "source", "ingested_at", "available_time",
    ]
    for col in ["open", "high", "low", "close", "volume", "open_interest"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.drop_duplicates(["date", "series_id"]).sort_values(["series_id", "date"])
    path = os.path.join(OUT_DIR, "main_sina.parquet")
    df.to_parquet(path, index=False)
    print("SAVED", path, len(df), flush=True)


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    try:
        download_main()
        download_contracts()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
