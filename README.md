# AI Cloud Cost Detective

Upload a cloud billing CSV and find unusual cost spikes, newly appearing services and savings opportunities.
All numbers (totals, trends, anomalies, forecast) are computed in code with pandas. Gemini is used only to
explain the findings in plain language, and the app keeps working if Gemini fails.

**Live demo:** https://cloud-cost-detective131.streamlit.app
**Demo video (about 2 min):** https://drive.google.com/file/d/18oMd0kjin6HVJJAV7iw5_2L7n9q7dgJ9/view?usp=drivesdk

> The live demo starts with a small synthetic sample. To see the real public-data results below, upload the
> cleaned FOCUS file (see "Data").

## Who it is for

Founders and DevOps/FinOps engineers who notice that the cloud bill suddenly grew and want to know
which service, which days and roughly how much extra it cost.

## How it works

```
CSV -> loader (validation) -> analysis + anomaly detection (code) -> Gemini (explanation only) -> Streamlit UI
```

- **Validation:** invalid dates, empty or negative costs and duplicate rows are dropped and reported to the user.
- **Anomaly detection (rule-based):**
  - Spike: a day is flagged when cost is at least 3 standard deviations and 1.5x above a rolling baseline of the
    previous 14 days. Days already flagged are excluded from the baseline, so a multi-day spike is caught as one incident.
  - New service: a service with no earlier history that appears above a minimum daily cost.
  - Tiny services (average below 2 USD/day) are ignored to reduce noise.
- **Incidents:** consecutive flagged days of one service are merged into a single incident with an "extra cost vs baseline".
- **Forecast:** a simple linear trend on the last 14 days. It is a rough estimate, not a guarantee.
- **Gemini:** writes 2-3 sentences per incident (what happened, possible causes, next step). If there is no API key,
  or Gemini returns an error or hits the free-tier rate limit, a template explanation is shown and the page is unaffected.

## Setup (Windows PowerShell)

```powershell
python -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env      # then put your key in .env: GEMINI_API_KEY=...
streamlit run app.py
```

The API key is read from `.env` locally (never committed) or from Streamlit Secrets when deployed.

## Data

Real public data: the FinOps Foundation FOCUS sample data
([FinOps-Open-Cost-and-Usage-Spec/FOCUS-Sample-Data](https://github.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS-Sample-Data)),
the 100,000-row file. It is anonymized billing data (AWS and Azure services mixed) for September 2024.

Download and prepare it:

```powershell
Invoke-WebRequest "https://raw.githubusercontent.com/FinOps-Open-Cost-and-Usage-Spec/FOCUS-Sample-Data/main/FOCUS-1.0/focus_sample_100000.csv.gz" -OutFile data\focus_sample_100000.csv.gz
python prepare_focus_data.py data/focus_sample_100000.csv.gz
```

This writes `data/hf_billing_clean.csv` (the file name is kept because the tests read it). Result on this dataset:
30 days, 94 services, total cost 2,875.19 USD.

**Main finding:** Amazon Elastic Compute Cloud ran about 428 USD above its baseline from 2024-09-11 to 2024-09-19
(9 days in a row), plus a separate spike of about 114 USD on 2024-09-24.

`generate_sample.py` creates a small synthetic file (`data/sample_billing.csv`) used by the demo's "Use sample data" option.

## Tests: 25/25 passing

```powershell
python -m pytest tests -v
```

Run `prepare_focus_data.py` first; the tests read `data/hf_billing_clean.csv`.

| Group | Cases | What it checks |
|---|---|---|
| Easy | 10 | totals, shares, trends and forecast on the real data |
| Tricky | 6 | pinned to the real incidents (EC2 9-day incident, Sep 24 spike, new-service rule, low false-positive rate) |
| Malformed input | 3 | missing column, bad rows reported, header-only file |
| Unknown / unavailable | 3 | missing file, no API key, simulated Gemini outage |
| Risky input | 3 | spreadsheet formula injection, API key never leaks, mixed currencies |

24 of the 25 cases are built from the public dataset. Only "file does not exist" cannot be.
These are regression tests: they check that results stay stable. I checked the detected incidents by hand,
but I did not measure precision/recall on labelled data.

## Problems found and fixed

1. A long spike polluted its own baseline, so days 3-4 of a 4-day spike were missed. Fixed by excluding already-flagged
   days from the baseline (extra cost on the synthetic test rose from 196.98 to 426.24).
2. One stray date (2024-03-21) in the real data made the detector treat the whole month as "new services".
   Fixed by dropping isolated dates in `prepare_focus_data.py`.
3. My first column mapping picked a unit price as the cost column. Fixed by mapping the exact FOCUS columns.
4. Gemini sometimes wrote "I will now examine the logs", which it cannot do. Fixed in the prompt.

## Limitations

- Anonymized sample data mixing AWS and Azure service names; it is not a real company's bill.
- Rule-based detection with fixed thresholds: low-cost services can still produce false alerts.
- The forecast is a simple linear estimate and is pulled up by recent spikes.
- Credits and negative costs are excluded, not netted against charges.
- Gemini only suggests possible causes. It has no access to a cloud account, and on the free tier it can hit rate limits
  (the template fallback is shown then).
- Only one CSV layout is supported: `date, service, category, region, cost, currency`.

## Project structure

```
app.py                  Streamlit UI
src/loader.py           CSV reading and validation
src/analysis.py         totals, trends, breakdowns
src/anomaly.py          spike / new-service detection, incidents, savings hints, forecast
src/explainer.py        Gemini explanations with fallback
prepare_focus_data.py   converts FOCUS sample data to the app's schema
generate_sample.py      small synthetic sample
tests/                  25 pytest cases
```
