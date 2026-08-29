"""Deliverable 1 -- the AI model.

A calibrated gradient-boosted classifier that predicts P(default) per applicant.
Calibration matters more than raw AUC here: the portfolio optimiser multiplies these
probabilities by cash amounts, so a miscalibrated 0.3 that should be 0.5 corrupts every
downstream coefficient of the QUBO. We therefore report Brier score and a reliability
curve alongside AUC.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

import data as data_mod

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"
RANDOM_STATE = 42


def _split_columns(X: pd.DataFrame):
    """Explicit column typing.

    Do NOT sniff with `dtype == object` -- this pandas gives string columns a dedicated
    `str` dtype, so that test silently returns False and the categoricals get handed to
    StandardScaler. Drive the split off the schema instead.
    """
    num = [c for c in X.columns if c in data_mod.NUMERIC]
    cat = [c for c in X.columns if c not in num]
    return num, cat


def build_model(X: pd.DataFrame) -> Pipeline:
    num, cat = _split_columns(X)
    pre = ColumnTransformer(
        [
            ("num", StandardScaler(), num),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
        ]
    )
    clf = HistGradientBoostingClassifier(
        max_iter=300,
        learning_rate=0.06,
        max_leaf_nodes=15,
        l2_regularization=1.0,
        early_stopping=True,
        validation_fraction=0.15,
        random_state=RANDOM_STATE,
    )
    # Isotonic needs more data than we have per fold; sigmoid (Platt) is the safe choice at n=1000.
    calibrated = CalibratedClassifierCV(clf, method="sigmoid", cv=StratifiedKFold(5, shuffle=True, random_state=RANDOM_STATE))
    return Pipeline([("pre", pre), ("clf", calibrated)])


def build_baseline(X: pd.DataFrame) -> Pipeline:
    """Honest, tuned classical baseline -- not a strawman."""
    num, cat = _split_columns(X)
    pre = ColumnTransformer(
        [
            ("num", StandardScaler(), num),
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), cat),
        ]
    )
    return Pipeline([("pre", pre), ("clf", LogisticRegression(max_iter=2000, C=0.5))])


def train(seed: int = RANDOM_STATE):
    df = data_mod.add_loan_economics(data_mod.load())
    X, y = data_mod.xy(df)

    idx = np.arange(len(df))
    tr, te = train_test_split(idx, test_size=0.30, stratify=y, random_state=seed)

    model = build_model(X)
    model.fit(X.iloc[tr], y[tr])
    base = build_baseline(X)
    base.fit(X.iloc[tr], y[tr])

    p_gb = model.predict_proba(X.iloc[te])[:, 1]
    p_lr = base.predict_proba(X.iloc[te])[:, 1]

    metrics = {
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
        "gbm_auc": float(roc_auc_score(y[te], p_gb)),
        "gbm_brier": float(brier_score_loss(y[te], p_gb)),
        "logreg_auc": float(roc_auc_score(y[te], p_lr)),
        "logreg_brier": float(brier_score_loss(y[te], p_lr)),
        "base_rate": float(y.mean()),
    }

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "ai_metrics.json").write_text(json.dumps(metrics, indent=2))

    # Score the full population so the demo can draw candidate pools from held-out rows only.
    p_all = np.full(len(df), np.nan)
    p_all[te] = p_gb
    df_scored = df.copy()
    df_scored["p_default"] = p_all
    df_scored["is_test"] = False
    df_scored.loc[df_scored.index[te], "is_test"] = True
    df_scored["expected_value"] = np.nan
    mask = df_scored["is_test"]
    df_scored.loc[mask, "expected_value"] = data_mod.expected_value(
        df_scored[mask], df_scored.loc[mask, "p_default"].to_numpy()
    )
    # 30k rows x 25 cols of scored output is 8 MB of CSV that nothing downstream reads in
    # full; keep only the held-out rows the optimiser can actually draw from.
    df_scored = df_scored[df_scored["is_test"]].copy()
    df_scored.to_csv(ARTIFACTS / "scored_applicants.csv", index=False)

    return model, metrics, df_scored


if __name__ == "__main__":
    _, m, scored = train()
    print(json.dumps(m, indent=2))
    print("\nscored test-set rows:", int(scored["is_test"].sum()))
    print(scored[["principal", "p_default", "expected_value"]].describe().round(2))
