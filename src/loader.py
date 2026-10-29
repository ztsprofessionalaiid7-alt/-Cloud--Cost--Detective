import sys
import pandas as pd

REQUIRED = ["date", "service", "category", "region", "cost", "currency"]


def load_billing_csv(source):
    """Read a billing CSV and return (clean DataFrame, list of issues)."""
    issues = []

    try:
        df = pd.read_csv(source)
    except Exception as e:
        raise ValueError(f"Could not read CSV: {e}")
    if df.empty:
        raise ValueError("CSV file is empty")

    df.columns = [c.strip().lower() for c in df.columns]
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    df = df[REQUIRED].copy()

    # date
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    bad = df["date"].isna().sum()
    if bad:
        issues.append(f"{bad} rows with invalid date dropped")
        df = df.dropna(subset=["date"])

    # cost
    df["cost"] = pd.to_numeric(df["cost"], errors="coerce")
    bad = df["cost"].isna().sum()
    if bad:
        issues.append(f"{bad} rows with empty/invalid cost dropped")
        df = df.dropna(subset=["cost"])

    neg = (df["cost"] < 0).sum()
    if neg:
        issues.append(f"{neg} rows with negative cost dropped (may be credits/refunds)")
        df = df[df["cost"] >= 0]

    # duplicates
    dup = df.duplicated().sum()
    if dup:
        issues.append(f"{dup} duplicate rows dropped")
        df = df.drop_duplicates()

    # currency
    currencies = df["currency"].astype(str).str.upper().unique()
    if len(currencies) > 1:
        issues.append(f"Multiple currencies found: {list(currencies)}; totals may be misleading")

    if df.empty:
        raise ValueError("No valid rows left after validation")

    return df.reset_index(drop=True), issues


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_billing.csv"
    data, problems = load_billing_csv(path)
    print(f"Valid rows: {len(data)}")
    print(f"Total cost: {data['cost'].sum():.2f}")
    print("Issues:", problems if problems else "none")