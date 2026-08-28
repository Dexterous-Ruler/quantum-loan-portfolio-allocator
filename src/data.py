"""UCI Statlog (German Credit) loader + loan economics.

Source: https://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data
1000 applicants, 20 attributes, binary target (1 = good/repaid, 2 = bad/default).
"""
from __future__ import annotations

import ssl
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd

DATA_URL = "https://archive.ics.uci.edu/ml/machine-learning-databases/statlog/german/german.data"
RAW = Path(__file__).resolve().parent.parent / "data" / "german.raw"

COLUMNS = [
    "checking_status", "duration_months", "credit_history", "purpose", "credit_amount",
    "savings_status", "employment_since", "installment_rate", "personal_status_sex",
    "other_debtors", "residence_since", "property", "age_years", "other_installment_plans",
    "housing", "existing_credits", "job", "num_dependents", "telephone", "foreign_worker",
    "target",
]

NUMERIC = [
    "duration_months", "credit_amount", "installment_rate", "residence_since",
    "age_years", "existing_credits", "num_dependents",
]

# Attribute 9 encodes personal status AND sex jointly.
# A91 male:divorced  A92 female:div/sep/married  A93 male:single  A94 male:married/widowed  A95 female:single
FEMALE_CODES = {"A92", "A95"}


def download(force: bool = False) -> Path:
    RAW.parent.mkdir(parents=True, exist_ok=True)
    if RAW.exists() and not force:
        return RAW
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(DATA_URL, timeout=30, context=ctx) as r:
        RAW.write_bytes(r.read())
    return RAW


def load() -> pd.DataFrame:
    """Return the raw frame with a clean binary `default` target and a `sex` column."""
    path = download()
    df = pd.read_csv(path, sep=r"\s+", header=None, names=COLUMNS)
    assert len(df) == 1000, f"expected 1000 rows, got {len(df)}"

    # Target: dataset codes 1 = good, 2 = bad. We model P(default), so bad -> 1.
    df["default"] = (df["target"] == 2).astype(int)
    df = df.drop(columns=["target"])

    # Protected attribute for the fairness constraint.
    df["sex"] = np.where(df["personal_status_sex"].isin(FEMALE_CODES), "female", "male")
    return df


def add_loan_economics(df: pd.DataFrame, apr: float = 0.12, lgd: float = 0.60) -> pd.DataFrame:
    """Attach the cash-flow terms the optimiser needs.

    apr  -- flat annual percentage rate the lender charges.
    lgd  -- loss given default, i.e. fraction of principal lost when a loan goes bad.
    """
    out = df.copy()
    out["principal"] = out["credit_amount"].astype(float)
    out["interest_if_repaid"] = out["principal"] * apr * (out["duration_months"] / 12.0)
    out["loss_if_default"] = out["principal"] * lgd
    return out


def expected_value(df: pd.DataFrame, p_default: np.ndarray) -> np.ndarray:
    """Risk-adjusted expected profit per loan.

    EV = P(repay) * interest  -  P(default) * LGD * principal

    This is the quantity the portfolio optimiser maximises. It is where the AI model
    feeds the quantum module: p_default comes from the classifier, and it sets the
    linear coefficients of the QUBO cost Hamiltonian.
    """
    p_default = np.asarray(p_default, dtype=float)
    return (1.0 - p_default) * df["interest_if_repaid"].to_numpy() - p_default * df["loss_if_default"].to_numpy()


FEATURES = [c for c in COLUMNS if c not in ("target",)]


def xy(df: pd.DataFrame):
    """Feature matrix / target, excluding the protected attribute and its parent column.

    We deliberately drop `personal_status_sex` and `sex` from the model inputs. That does
    NOT make the model fair (proxies remain) -- it just means unfairness has to be measured
    on outcomes, which is what the fairness constraint in the optimiser does.
    """
    drop = ["default", "sex", "personal_status_sex", "principal", "interest_if_repaid", "loss_if_default"]
    X = df.drop(columns=[c for c in drop if c in df.columns])
    y = df["default"].to_numpy()
    return X, y
