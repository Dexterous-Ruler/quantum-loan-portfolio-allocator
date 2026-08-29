"""UCI "Default of Credit Card Clients" (Taiwan, 2005) loader + loan economics.

Source: https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients
30,000 clients, 23 predictors, binary target (1 = defaulted next month).

WHY THIS DATASET, AND NOT GERMAN CREDIT
---------------------------------------
We started on UCI Statlog (German Credit), the usual credit-scoring benchmark, and moved off
it deliberately. It is 1,000 rows of 1973-75 West German lending, its 30% default rate is an
artefact of a stratified sample with bad credits heavily oversampled (700 good / 300 bad by
construction), and Groemping (2019), "South German Credit Data: Correcting a Widely Used Data
Set" (Report 4/2019, Beuth University of Applied Sciences Berlin), showed several of its
variable codings are simply wrong. In particular sex is NOT recoverable: male singles and
female non-singles share code A92, and A95 (female:single) has zero rows in the published
file, so any "female" group is a mixed bag.

This dataset fixes every one of those:
  * 30,000 rows rather than 1,000
  * 2005 rather than 1973-75
  * a REAL 22.1% default rate, not a constructed one -- so expected values are in real money
  * sex, age, education and marital status are all coded unambiguously, which means the
    fairness constraint operates on an attribute that means what it says

ECONOMICS
---------
This is revolving credit, so the exposure at default is the outstanding balance, not the
credit limit. We use the most recent statement balance clipped to [0, limit]: a customer with
a NT$500,000 limit and a NT$12,000 balance puts NT$12,000 at risk, not NT$500,000. Using the
limit instead would overstate every position by roughly an order of magnitude.
"""
from __future__ import annotations

import io
import ssl
import urllib.request
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

DATA_URL = "https://archive.ics.uci.edu/static/public/350/default+of+credit+card+clients.zip"
RAW = Path(__file__).resolve().parent.parent / "data" / "taiwan.zip"
XLS_NAME = "default of credit card clients.xls"

TARGET = "default payment next month"

# Repayment-status history (PAY_*) is the dominant signal in this dataset; bill and payment
# amounts add the rest. AGE stays a feature -- sex is the protected attribute here, and unlike
# German Credit it is coded unambiguously.
NUMERIC = [
    "LIMIT_BAL", "AGE",
    "PAY_0", "PAY_2", "PAY_3", "PAY_4", "PAY_5", "PAY_6",
    "BILL_AMT1", "BILL_AMT2", "BILL_AMT3", "BILL_AMT4", "BILL_AMT5", "BILL_AMT6",
    "PAY_AMT1", "PAY_AMT2", "PAY_AMT3", "PAY_AMT4", "PAY_AMT5", "PAY_AMT6",
]

# EDUCATION codes 0, 4, 5 and 6 are undocumented or "other" and are individually tiny;
# folding them together avoids near-empty one-hot columns.
EDUCATION_LABELS = {1: "graduate", 2: "university", 3: "high-school"}
MARRIAGE_LABELS = {1: "married", 2: "single", 3: "other"}


def download(force: bool = False) -> Path:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    if RAW.exists() and not force:
        return RAW
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(DATA_URL, timeout=120, context=ctx) as r:
        RAW.write_bytes(r.read())
    return RAW


def load() -> pd.DataFrame:
    """Return the frame with a clean binary `default`, a protected `group`, and a `sector`."""
    path = download()
    with zipfile.ZipFile(path) as z:
        # Row 0 is a merged banner; the real header is row 1.
        df = pd.read_excel(io.BytesIO(z.read(XLS_NAME)), header=1)

    assert len(df) == 30000, f"expected 30000 rows, got {len(df)}"
    df = df.drop(columns=["ID"])
    df["default"] = df[TARGET].astype(int)
    df = df.drop(columns=[TARGET])

    # Protected attribute. Unlike German Credit's attribute 9, this one is unambiguous.
    df["group"] = np.where(df["SEX"] == 2, "female", "male")

    # Concentration axis for the diversification term. Retail books are managed against
    # segment limits, and education band is the cleanest segment this dataset offers.
    df["sector"] = df["EDUCATION"].map(EDUCATION_LABELS).fillna("other")
    df["marital"] = df["MARRIAGE"].map(MARRIAGE_LABELS).fillna("other")
    return df


def add_loan_economics(df: pd.DataFrame, apr: float = 0.18, lgd: float = 0.60) -> pd.DataFrame:
    """Attach the cash-flow terms the optimiser needs.

    apr  -- annual percentage rate on revolving balances. 18% is typical of Taiwanese card
            lending in this period and higher than an instalment-loan rate, which is the
            point: card APRs price in exactly the default risk we are modelling.
    lgd  -- loss given default, the fraction of exposure lost when an account goes bad.

    Only the RATIO lgd/apr affects which accounts get funded -- see src/sensitivity.py.
    """
    out = df.copy()
    # Exposure at default: the outstanding balance, floored at zero (overpayments show as
    # negative bills) and capped at the credit limit.
    out["principal"] = np.clip(out["BILL_AMT1"], 0, out["LIMIT_BAL"]).astype(float)
    out["interest_if_repaid"] = out["principal"] * apr
    out["loss_if_default"] = out["principal"] * lgd
    return out


def expected_value(df: pd.DataFrame, p_default: np.ndarray) -> np.ndarray:
    """Risk-adjusted expected profit per account.

    EV = P(repay) * interest  -  P(default) * LGD * exposure

    This is where the AI model feeds the quantum module: p_default comes from the classifier
    and sets the linear coefficients of the QUBO cost Hamiltonian.
    """
    p_default = np.asarray(p_default, dtype=float)
    return ((1.0 - p_default) * df["interest_if_repaid"].to_numpy()
            - p_default * df["loss_if_default"].to_numpy())


def xy(df: pd.DataFrame):
    """Feature matrix / target, excluding the protected attribute and derived economics.

    `SEX` and the `group` label built from it are dropped so the classifier cannot condition
    on sex directly. That does NOT make the model fair -- proxies remain -- it means unfairness
    has to be measured on outcomes, which is what the optimiser's fairness term does.
    """
    drop = ["default", "group", "SEX", "sector", "marital",
            "principal", "interest_if_repaid", "loss_if_default"]
    X = df.drop(columns=[c for c in drop if c in df.columns])
    return X, df["default"].to_numpy()
