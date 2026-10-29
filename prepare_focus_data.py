import sys
import pandas as pd

SRC = sys.argv[1] if len(sys.argv) > 1 else "data/focus_sample.csv"
OUT = "data/hf_billing_clean.csv"   # tests read this file name; it now holds FOCUS data
MAX_GAP_DAYS = 7                    # gap larger than this splits the data into clusters

# Standard FOCUS 1.0 column names
MAP = {
    "date": "ChargePeriodStart",
    "service": "ServiceName",
    "category": "ServiceCategory",
    "region": "RegionName",
    "cost": "BilledCost",
    "currency": "BillingCurrency",
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
df["date"] = (pd.to_datetime(raw[MAP["date"]], errors="coerce", utc=True)
              .dt.tz_localize(None).dt.normalize())
df["service"] = raw[MAP["service"]].fillna("unknown").astype(str).str.strip()
df["category"] = raw[MAP["category"]].fillna("unknown").astype(str).str.strip()
df["region"] = raw[MAP["region"]].fillna("unknown").astype(str).str.strip()
df["cost"] = pd.to_numeric(raw[MAP["cost"]], errors="coerce")
df["currency"] = raw[MAP["currency"]].fillna("USD").astype(str).str.upper().str.strip()

before = len(df)
df = df.dropna(subset=["date", "cost"])
invalid = before - len(df)
neg = int((df["cost"] < 0).sum())
df = df[df["cost"] >= 0]          # credits/refunds are excluded

if df.empty:
    print("No valid rows after cleaning.")
    sys.exit(1)

# Keep only the main continuous period; drop isolated stray dates
dates = pd.to_datetime(sorted(df["date"].unique()))
clusters, cur = [], [dates[0]]
for d in dates[1:]:
    if (d - cur[-1]).days > MAX_GAP_DAYS:
        clusters.append(cur)
        cur = [d]
    else:
        cur.append(d)
clusters.append(cur)
main = max(clusters, key=len)
mask = (df["date"] >= main[0]) & (df["date"] <= main[-1])
stray_rows = int((~mask).sum())
stray_days = sorted({d.date().isoformat() for d in df.loc[~mask, "date"]})
df = df[mask]

df = (df.groupby(["date", "service", "category", "region", "currency"], as_index=False)["cost"]
        .sum())
df["cost"] = df["cost"].round(4)
df.to_csv(OUT, index=False)

print(f"Invalid dropped: {invalid} | negative dropped: {neg}")
print(f"Stray rows dropped: {stray_rows} (dates: {stray_days})")
print(f"Saved {len(df)} rows -> {OUT}")
print(f"Date range: {df['date'].min().date()} to {df['date'].max().date()}")
print(f"Days: {df['date'].nunique()} | Services: {df['service'].nunique()} | "
      f"Regions: {df['region'].nunique()} | Categories: {df['category'].nunique()}")
print("Currencies:", list(df["currency"].unique()))
print(f"Total cost: {df['cost'].sum():,.2f}")