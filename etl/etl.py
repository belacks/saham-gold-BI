import os
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# ── Configuration ────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

DATA_DIR = PROJECT_ROOT / "data" / "raw"

# Ticker metadata — static info for dim_ticker
TICKER_META = {
    "EMAS": {
        "company_name": "PT Merdeka Gold Resources Tbk",
        "exchange": "IDX",
        "sector": "Basic Materials",
    },
    "GOLD": {
        "company_name": "PT Visi Telekomunikasi Infrastruktur Tbk",
        "exchange": "IDX",
        "sector": "Telecommunications",
    },
}


# ── Helper functions ─────────────────────────────────────────
def parse_indo_price(value: str) -> float:
    """Convert Indonesian price format to float.

    '8.525,00' → 8525.00   (dot=thousands, comma=decimal)
    '290'      → 290.0     (no separators)
    """
    if pd.isna(value):
        return np.nan
    s = str(value).strip().strip('"')
    s = s.replace(".", "")   # remove thousands separator
    s = s.replace(",", ".")  # comma → decimal point
    return float(s)


def parse_indo_volume(value: str) -> int:
    """Convert Indonesian volume with K/M suffix to int64.

    '9,09M'   → 9_090_000
    '155,30K'  → 155_300
    '0,20K'   → 200
    """
    if pd.isna(value):
        return 0
    s = str(value).strip().strip('"')

    multiplier = 1
    if s.endswith("M"):
        multiplier = 1_000_000
        s = s[:-1]
    elif s.endswith("K"):
        multiplier = 1_000
        s = s[:-1]
    elif s.endswith("B"):
        multiplier = 1_000_000_000
        s = s[:-1]

    s = s.replace(".", "")   # remove thousands separator (if any)
    s = s.replace(",", ".")  # comma → decimal point
    return int(float(s) * multiplier)


def parse_indo_pct(value: str) -> float:
    """Convert Indonesian percentage string to float.

    '-2,01%' → -2.01
    '4,50%'  → 4.50
    """
    if pd.isna(value):
        return np.nan
    s = str(value).strip().strip('"')
    s = s.replace("%", "")
    s = s.replace(",", ".")
    return float(s)


# ── Step 1: Extract ──────────────────────────────────────────
def extract() -> pd.DataFrame:
    """Read both CSVs, tag with ticker_code, and concatenate."""
    files = {
        "EMAS": DATA_DIR / "Data Historis EMAS.csv",
        "GOLD": DATA_DIR / "Data Historis GOLD.csv",
    }

    frames = []
    for ticker, path in files.items():
        df = pd.read_csv(path, encoding="utf-8-sig")
        df["ticker_code"] = ticker
        frames.append(df)
        print(f"  Extracted {ticker}: {len(df)} rows")

    combined = pd.concat(frames, ignore_index=True)
    print(f"  Total extracted: {len(combined)} rows")
    return combined


# ── Step 2: Transform dates ──────────────────────────────────
def transform_dates(df: pd.DataFrame) -> pd.DataFrame:
    """Parse Tanggal and derive date dimension columns."""
    df["full_date"] = pd.to_datetime(df["Tanggal"], dayfirst=True)
    df["year"] = df["full_date"].dt.year
    df["quarter"] = df["full_date"].dt.quarter
    df["month"] = df["full_date"].dt.month
    df["month_name"] = df["full_date"].dt.month_name()
    # Monday=1, Sunday=7 (ISO standard)
    df["day_of_week"] = df["full_date"].dt.dayofweek + 1
    df["day_name"] = df["full_date"].dt.day_name()
    return df


# ── Step 3: Transform numbers ────────────────────────────────
def transform_numbers(df: pd.DataFrame) -> pd.DataFrame:
    """Convert Indonesian-formatted number columns to proper numerics."""
    # Price columns
    for col in ["Terakhir", "Pembukaan", "Tertinggi", "Terendah"]:
        df[col] = df[col].apply(parse_indo_price)

    # Volume
    df["Vol."] = df["Vol."].apply(parse_indo_volume)

    # Change percentage
    df["Perubahan%"] = df["Perubahan%"].apply(parse_indo_pct)

    # Rename to English for clarity
    df = df.rename(columns={
        "Terakhir":   "close_price",
        "Pembukaan":  "open_price",
        "Tertinggi":  "high_price",
        "Terendah":   "low_price",
        "Vol.":       "volume",
        "Perubahan%": "change_pct",
    })

    return df


# ── Step 4: Load dim_date ────────────────────────────────────
def load_dim_date(df: pd.DataFrame, engine) -> pd.DataFrame:
    """Insert unique dates into dim_date, return mapping with date_id."""
    date_cols = ["full_date", "year", "quarter", "month",
                 "month_name", "day_of_week", "day_name"]
    dim = df[date_cols].drop_duplicates(subset=["full_date"]).copy()
    dim = dim.sort_values("full_date").reset_index(drop=True)

    insert_sql = text("""
        INSERT INTO dim_date (full_date, year, quarter, month,
                              month_name, day_of_week, day_name)
        VALUES (:full_date, :year, :quarter, :month,
                :month_name, :day_of_week, :day_name)
        ON CONFLICT (full_date) DO NOTHING
    """)

    with engine.begin() as conn:
        for _, row in dim.iterrows():
            conn.execute(insert_sql, {
                "full_date":   row["full_date"].date(),
                "year":        int(row["year"]),
                "quarter":     int(row["quarter"]),
                "month":       int(row["month"]),
                "month_name":  row["month_name"],
                "day_of_week": int(row["day_of_week"]),
                "day_name":    row["day_name"],
            })

    # Query back to get database-generated date_id values
    dim_date_db = pd.read_sql("SELECT * FROM dim_date", engine)
    print(f"  dim_date: {len(dim_date_db)} rows in DB")
    return dim_date_db


# ── Step 5: Load dim_ticker ──────────────────────────────────
def load_dim_ticker(engine) -> pd.DataFrame:
    """Insert ticker metadata into dim_ticker, return mapping with ticker_id."""
    insert_sql = text("""
        INSERT INTO dim_ticker (ticker_code, company_name, exchange, sector)
        VALUES (:ticker_code, :company_name, :exchange, :sector)
        ON CONFLICT (ticker_code) DO NOTHING
    """)

    with engine.begin() as conn:
        for ticker_code, meta in TICKER_META.items():
            conn.execute(insert_sql, {
                "ticker_code":  ticker_code,
                "company_name": meta["company_name"],
                "exchange":     meta["exchange"],
                "sector":       meta["sector"],
            })

    dim_ticker_db = pd.read_sql("SELECT * FROM dim_ticker", engine) 
    print(f"  dim_ticker: {len(dim_ticker_db)} rows in DB")
    return dim_ticker_db


# ── Step 6: Load fact_stock_prices ───────────────────────────
def load_fact(df: pd.DataFrame, dim_date: pd.DataFrame,
              dim_ticker: pd.DataFrame, engine) -> None:
    """Merge dimension IDs and insert into fact_stock_prices."""
    # Merge date_id
    dim_date["full_date"] = pd.to_datetime(dim_date["full_date"])
    merged = df.merge(dim_date[["date_id", "full_date"]], on="full_date", how="left")

    # Merge ticker_id
    merged = merged.merge(dim_ticker[["ticker_id", "ticker_code"]],
                          on="ticker_code", how="left")

    # Select fact columns
    fact = merged[["date_id", "ticker_id", "open_price", "close_price",
                   "high_price", "low_price", "volume", "change_pct"]].copy()

    insert_sql = text("""
        INSERT INTO fact_stock_prices
            (date_id, ticker_id, open_price, close_price,
             high_price, low_price, volume, change_pct)
        VALUES
            (:date_id, :ticker_id, :open_price, :close_price,
             :high_price, :low_price, :volume, :change_pct)
        ON CONFLICT (date_id, ticker_id) DO NOTHING
    """)

    with engine.begin() as conn:
        rows = fact.to_dict("records")
        for row in rows:
            # Convert numpy types to Python native for psycopg2
            conn.execute(insert_sql, {
                "date_id":     int(row["date_id"]),
                "ticker_id":   int(row["ticker_id"]),
                "open_price":  float(row["open_price"]),
                "close_price": float(row["close_price"]),
                "high_price":  float(row["high_price"]),
                "low_price":   float(row["low_price"]),
                "volume":      int(row["volume"]),
                "change_pct":  float(row["change_pct"]),
            })

    print(f"  fact_stock_prices: {len(fact)} rows inserted/skipped")


# ── Main ─────────────────────────────────────────────────────
def main():
    print("=" * 55)
    print("  Stockbit BI — ETL Pipeline")
    print("=" * 55)

    engine = create_engine(DATABASE_URL)

    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("\n✔ Database connection OK\n")

    print("[1/5] Extracting CSV data...")
    df = extract()

    print("\n[2/5] Transforming dates...")
    df = transform_dates(df)

    print("[3/5] Transforming numbers...")
    df = transform_numbers(df)

    print("\n[4/5] Loading dim_date...")
    dim_date = load_dim_date(df, engine)

    print("\n[5/5] Loading dim_ticker...")
    dim_ticker = load_dim_ticker(engine)

    print("\n[6/6] Loading fact_stock_prices...")
    load_fact(df, dim_date, dim_ticker, engine)

    # Summary
    with engine.connect() as conn:
        counts = {}
        for table in ["dim_date", "dim_ticker", "fact_stock_prices"]:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = result.scalar()

    print("\n" + "=" * 55)
    print("  ETL Complete — Final Row Counts")
    print("=" * 55)
    for table, count in counts.items():
        print(f"  {table:<25} {count:>6} rows")
    print()


if __name__ == "__main__":
    main()
