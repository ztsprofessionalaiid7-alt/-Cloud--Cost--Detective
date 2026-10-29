import sys
import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/hf_gcp_billing.csv"
OUT = "data/hf_billing_clean.csv"

# Column names of the Hugging Face dataset sairamn/gcp-cloud-billing-cost
MAP = {
    "date": "Usage Start Date",
    "service": "Service Name",
    "category": "Usage Unit",      # no category column in this dataset
    "region": "Region / Zone",
    "cost": "Unrounded Cost ($)",  # USD
}

raw = pd.read_csv(SRC, low_memory=False)
raw.columns = [c.strip() for c in raw.columns]
print("Raw rows:", len(raw))

missing = [v for v in MAP.values() if v not in raw.columns]
if missing:
    print("Columns not found:", missing)
    print("Available:", list(raw.columns))
    sys.exit(1)

df = pd.DataFrame()
df["date"] = pd.to_datetime(raw[MAP["date"]], errors="coerce").dt.normalize()
df["service"] = raw[MAP["service"]].astype(str).str.strip()
df["category"] = raw[MAP["category"]].astype(str).str.strip()
df["region"] = raw[MAP["region"]].astype(str).str.strip()
df["cost"] = pd.to_numeric(raw[MAP["cost"]], errors="coerce")
df["currency"] = "USD"

before = len(df)
df = df.dropna(subset=["date", "cost"])
invalid = before - len(df)
neg = int((df["cost"] < 0).sum())
df = df[df["cost"] >= 0]

if df.empty:
    print("No valid rows after cleaning.")
    sys.exit(1)

df = (df.groupby(["date", "service", "category", "region", "currency"], as_index=False)["cost"]
        .sum())
df["cost"] = df["cost"].round(4)
df.to_csv(OUT, index=False)

print(f"Invalid dropped: {invalid} | negative dropped: {neg}")
print(f"Saved {len(df)} rows -> {OUT}")
print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
print(f"Days: {df['date'].nunique()} | Services: {df['service'].nunique()} | "
      f"Regions: {df['region'].nunique()}")
print(f"Total cost: {df['cost'].sum():,.2f} USD")