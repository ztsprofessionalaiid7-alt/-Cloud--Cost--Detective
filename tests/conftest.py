import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from loader import load_billing_csv  # noqa: E402

# Cleaned real public data (FinOps Foundation FOCUS sample), made by prepare_focus_data.py
HF_CLEAN = ROOT / "data" / "hf_billing_clean.csv"


@pytest.fixture(scope="session")
def hf():
    """Real public billing data, cleaned."""
    if not HF_CLEAN.exists():
        pytest.skip("Run prepare_focus_data.py first")
    df, _ = load_billing_csv(HF_CLEAN)
    return df


@pytest.fixture
def make_df():
    """Controlled daily series for cases that need a known ground truth."""
    def _make(service, costs, start="2026-01-01", region="us-central1",
              category="Compute", currency="USD"):
        dates = pd.date_range(start, periods=len(costs), freq="D")
        return pd.DataFrame({"date": dates, "service": service, "category": category,
                             "region": region, "cost": costs, "currency": currency})
    return _make