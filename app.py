import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

import pandas as pd
import streamlit as st
from loader import load_billing_csv
from analysis import summary, daily_trend, breakdown
from anomaly import (detect_anomalies, group_anomalies,
                     savings_opportunities, forecast_month_end)
from explainer import explain_incident

st.set_page_config(page_title="AI Cloud Cost Detective", layout="wide")
st.title("AI Cloud Cost Detective")
st.caption("Totals, charts and anomalies are computed in code. "
           "Gemini only explains them in plain language.")

uploaded = st.file_uploader("Upload billing CSV", type="csv")
use_sample = st.checkbox("Use sample data", value=uploaded is None)

source = uploaded if uploaded is not None else (
    "data/sample_billing.csv" if use_sample else None)

if source is None:
    st.info("Upload a CSV or tick 'Use sample data'.")
    st.stop()

try:
    df, issues = load_billing_csv(source)
except ValueError as e:
    st.error(str(e))
    st.stop()

for msg in issues:
    st.warning(msg)

s = summary(df)
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total cost", f"{s['total_cost']:,.2f}")
c2.metric("Avg daily", f"{s['avg_daily_cost']:,.2f}")
c3.metric("Days", s["days"])
c4.metric("Top service", s["top_service"])

st.subheader("Daily cost")
st.line_chart(daily_trend(df).set_index("date")["cost"])

left, right = st.columns(2)
with left:
    st.subheader("Top 15 services by cost")
    top15 = breakdown(df, "service").head(15).set_index("service")["cost"]
    st.bar_chart(top15, horizontal=True)
with right:
    st.subheader("By region")
    st.dataframe(breakdown(df, "region"), hide_index=True)

anoms = detect_anomalies(df)
incidents = group_anomalies(anoms)

st.subheader("Incidents")
if incidents.empty:
    st.success("No anomalies detected.")
else:
    st.dataframe(incidents, hide_index=True)
    use_ai = st.checkbox("Explain with Gemini", value=True)
    cache = st.session_state.setdefault("explanations", {})

    for _, inc in incidents.iterrows():
        key = (inc["service"], inc["start"], inc["end"])
        with st.expander(f"{inc['service']}: {inc['start']} to {inc['end']} "
                         f"(+{inc['extra_cost']:.2f})"):
            if not use_ai:
                st.write("AI explanation is turned off.")
                continue
            # Reuse a successful Gemini answer; retry only if it failed before
            if key not in cache or cache[key][1] != "gemini":
                cache[key] = explain_incident(inc.to_dict())
            text, src = cache[key]
            st.write(text)
            st.caption(f"Source: {src}")

st.subheader("Savings opportunities")
for t in savings_opportunities(df, incidents):
    st.write("-", t)

st.subheader("Forecast (simple linear trend)")
fc = forecast_month_end(df)
if fc:
    st.write(f"Next 30 days: **{fc['next_30_days_cost']:,.2f}** "
             f"(avg {fc['avg_daily_forecast']:,.2f}/day). "
             f"This is a rough estimate, not a guarantee.")
else:
    st.write("Not enough data for a forecast.")