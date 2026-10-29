import sys
import numpy as np
import pandas as pd
from loader import load_billing_csv

# Tunable thresholds
BASELINE_DAYS = 14      # days used to build the baseline
Z_THRESHOLD = 3.0       # how many std-devs above baseline = anomaly
MIN_RATIO = 1.5         # and at least this many times the baseline mean
MIN_DAILY_COST = 2.0    # ignore tiny services (noise)
NEW_SERVICE_MIN = 10.0  # new service: flag if daily cost above this


def detect_anomalies(df):
    """Rule-based anomaly detection per service (all regions combined)."""
    daily = df.groupby(["service", "date"], as_index=False)["cost"].sum()
    all_dates = sorted(daily["date"].unique())
    first_date = all_dates[0]
    anomalies = []

    for service, g in daily.groupby("service"):
        g = g.sort_values("date").reset_index(drop=True)
        service_start = g["date"].iloc[0]

        # Rule A: service has no history before it appeared
        if service_start > first_date and g["cost"].iloc[0] >= NEW_SERVICE_MIN:
            anomalies.append({
                "service": service,
                "date": service_start.date().isoformat(),
                "type": "new_service",
                "cost": round(g["cost"].iloc[0], 2),
                "baseline": 0.0,
                "ratio": None,
                "reason": f"{service} appeared for the first time (no baseline).",
            })
            continue  # no baseline to compare for the rest

        # Rule B: spike vs rolling baseline of previous NORMAL days
        flagged = set()
        for i in range(len(g)):
            if i < 7:   # need at least 7 days of history
                continue
            window = range(max(0, i - BASELINE_DAYS), i)
            normal_idx = [j for j in window if j not in flagged]
            if len(normal_idx) < 5:
                continue
            hist = g["cost"].iloc[normal_idx]
            mean, std = hist.mean(), hist.std(ddof=0)
            cost = g["cost"].iloc[i]
            if mean < MIN_DAILY_COST:
                continue
            std = max(std, mean * 0.05)  # avoid zero-variance blowups
            z = (cost - mean) / std
            ratio = cost / mean
            if z >= Z_THRESHOLD and ratio >= MIN_RATIO:
                flagged.add(i)
                anomalies.append({
                    "service": service,
                    "date": g["date"].iloc[i].date().isoformat(),
                    "type": "spike",
                    "cost": round(cost, 2),
                    "baseline": round(mean, 2),
                    "ratio": round(ratio, 2),
                    "reason": f"{service} cost is {ratio:.1f}x its recent average (z={z:.1f}).",
                })

    out = pd.DataFrame(anomalies)
    if out.empty:
        return out
    return out.sort_values(["service", "date"]).reset_index(drop=True)


def group_anomalies(anoms):
    """Merge consecutive daily anomalies of one service into incidents."""
    if anoms.empty:
        return anoms
    rows = []
    for service, g in anoms.groupby("service"):
        g = g.sort_values("date")
        dates = pd.to_datetime(g["date"]).tolist()
        prev = dates[0]
        idx = [0]
        for k in range(1, len(dates)):
            if (dates[k] - prev).days <= 1:
                idx.append(k)
            else:
                rows.append(_incident(service, g.iloc[idx]))
                idx = [k]
            prev = dates[k]
        rows.append(_incident(service, g.iloc[idx]))
    return pd.DataFrame(rows).sort_values("start").reset_index(drop=True)


def _incident(service, g):
    extra = (g["cost"] - g["baseline"]).sum()
    return {
        "service": service,
        "start": g["date"].iloc[0],
        "end": g["date"].iloc[-1],
        "days": len(g),
        "type": g["type"].iloc[0],
        "peak_cost": g["cost"].max(),
        "extra_cost": round(extra, 2),
    }


def savings_opportunities(df, incidents):
    """Simple, explainable savings hints computed from the data."""
    tips = []
    total = df["cost"].sum()
    if not incidents.empty:
        for _, r in incidents.iterrows():
            if r["extra_cost"] > 0:
                tips.append(
                    f"{r['service']}: investigate {r['start']} to {r['end']}; "
                    f"about {r['extra_cost']:.2f} above baseline could be avoided."
                )
    top = df.groupby("service")["cost"].sum().sort_values(ascending=False)
    if len(top) and top.iloc[0] / total > 0.4:
        tips.append(
            f"{top.index[0]} is {top.iloc[0] / total * 100:.0f}% of total spend; "
            f"review rightsizing / reserved capacity for it."
        )
    return tips


def forecast_month_end(df):
    """Linear-trend forecast of next 30 days from the last 14 days."""
    daily = df.groupby("date")["cost"].sum().sort_index()
    recent = daily.tail(14)
    if len(recent) < 5:
        return None
    x = np.arange(len(recent))
    slope, intercept = np.polyfit(x, recent.values, 1)
    future_x = np.arange(len(recent), len(recent) + 30)
    preds = np.maximum(slope * future_x + intercept, 0)
    return {
        "method": "linear trend on last 14 days",
        "next_30_days_cost": round(float(preds.sum()), 2),
        "avg_daily_forecast": round(float(preds.mean()), 2),
        "daily_trend_slope": round(float(slope), 2),
    }


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "data/sample_billing.csv"
    data, _ = load_billing_csv(path)

    anoms = detect_anomalies(data)
    print("=== DAILY ANOMALIES ===")
    print(anoms.to_string(index=False) if not anoms.empty else "none")

    incidents = group_anomalies(anoms)
    print("\n=== INCIDENTS ===")
    print(incidents.to_string(index=False) if not incidents.empty else "none")

    print("\n=== SAVINGS OPPORTUNITIES ===")
    for t in savings_opportunities(data, incidents):
        print("-", t)

    print("\n=== FORECAST ===")
    print(forecast_month_end(data))