import sys
import pandas as pd
from loader import load_billing_csv


def daily_trend(df):
    """Total cost per day."""
    out = df.groupby("date", as_index=False)["cost"].sum()
    out["cost"] = out["cost"].round(2)
    return out


def monthly_trend(df):
    """Total cost per month."""
    tmp = df.copy()
    tmp["month"] = tmp["date"].dt.to_period("M").astype(str)
    out = tmp.groupby("month", as_index=False)["cost"].sum()
    out["cost"] = out["cost"].round(2)
    return out


def breakdown(df, by):
    """Cost grouped by one or more columns, with % share, sorted high to low."""
    out = df.groupby(by, as_index=False)["cost"].sum()
    total = out["cost"].sum()
    out["share_pct"] = (out["cost"] / total * 100).round(1) if total else 0.0
    out["cost"] = out["cost"].round(2)
    return out.sort_values("cost", ascending=False).reset_index(drop=True)


def service_daily(df):
    """Daily cost per service (used later for anomaly detection)."""
    out = df.groupby(["date", "service"], as_index=False)["cost"].sum()
    return out


def summary(df):
    """Headline numbers."""
    days = df["date"].nunique()
    total = df["cost"].sum()
    return {
        "total_cost": round(total, 2),
        "days": int(days),
        "avg_daily_cost": round(total / days, 2) if days else 0.0,
        "start": df["date"].min().date().isoformat(),
        "end": df["date"].max().date().isoformat(),
        "top_service": breakdown(df, "service").iloc[0]["service"],
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_billing.csv"
    data, issues = load_billing_csv(path)

    print("=== SUMMARY ===")
    for k, v in summary(data).items():
        print(f"{k}: {v}")

    print("\n=== MONTHLY TREND ===")
    print(monthly_trend(data).to_string(index=False))

    print("\n=== BY SERVICE ===")
    print(breakdown(data, "service").to_string(index=False))

    print("\n=== BY REGION ===")
    print(breakdown(data, "region").to_string(index=False))

    print("\n=== BY CATEGORY ===")
    print(breakdown(data, "category").to_string(index=False))

    print("\n=== LAST 7 DAYS ===")
    print(daily_trend(data).tail(7).to_string(index=False))