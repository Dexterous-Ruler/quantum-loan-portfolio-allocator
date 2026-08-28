"""Does the chosen portfolio depend on the two numbers we invented?

The German Credit dataset contains no interest rate and no recovery rate, so the loan
economics in `data.add_loan_economics` (12% APR, 60% loss-given-default) are assumptions,
not measurements. Every expected-value coefficient -- and therefore the QUBO's ground
state -- rests on them. A judge is entitled to ask where they came from.

The answer turns out to be better than "we guessed". Expanding the expected value,

    EV_i = A_i * [ (1 - p_i) * apr * d_i/12  -  p_i * lgd ]
         = A_i * apr * [ (1 - p_i) * d_i/12  -  p_i * (lgd/apr) ]

so scaling apr and lgd together by any k > 0 scales every EV_i by k. A knapsack's argmax
is invariant under positive scaling of the objective, so **the selected portfolio depends
only on the ratio rho = lgd/apr, not on either number individually**. Our baseline
(12%, 0.60) is just one point on the line rho = 5.

That reduces two invented numbers to one, and this script measures sensitivity to that one.
Solved exactly (brute force), so the result reflects the problem, not solver noise.

Caveat: the invariance holds for the pure profit objective. With the fairness penalty
switched on it does NOT, because that penalty is not scaled alongside the EVs -- turning
lambda up is equivalent to weighting fairness more heavily relative to profit.

    python src/sensitivity.py        # ~1 minute
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import data as data_mod
import portfolio as pf
import solvers

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

BASE_APR, BASE_LGD = 0.12, 0.60
BASE_RHO = BASE_LGD / BASE_APR                      # 5.0
RHOS = [2.0, 3.0, 4.0, 5.0, 6.0, 7.5, 10.0]
SEEDS = list(range(8))
POOL_N = 10


def rescore(scored: pd.DataFrame, apr: float, lgd: float) -> pd.DataFrame:
    """Recompute loan economics and expected value under different assumptions.

    P(default) is untouched -- it comes from the classifier and does not depend on pricing.
    Only the cash-flow terms move, which is exactly the thing under test.
    """
    df = scored.copy()
    df["principal"] = df["credit_amount"].astype(float)
    df["interest_if_repaid"] = df["principal"] * apr * (df["duration_months"] / 12.0)
    df["loss_if_default"] = df["principal"] * lgd
    mask = df["is_test"] & df["p_default"].notna()
    df.loc[mask, "expected_value"] = data_mod.expected_value(
        df[mask], df.loc[mask, "p_default"].to_numpy()
    )
    return df


def selected_ids(scored: pd.DataFrame, apr: float, lgd: float, seed: int) -> set[int]:
    """Full pipeline: re-price, re-screen, re-optimise. Pool membership may change."""
    df = rescore(scored, apr, lgd)
    p = pf.build_problem(df, n=POOL_N, fairness_lambda=0.0, seed=seed)
    x = solvers.solve_bruteforce(p).x
    return {i for i, keep in zip(p.ids, x) if keep}


def selected_ids_fixed_pool(scored: pd.DataFrame, base: pf.PortfolioProblem,
                            apr: float, lgd: float) -> set[int]:
    """Re-price the SAME applicants and re-optimise, holding the pool fixed.

    Without this the measurement is confounded: `build_problem` screens to positive-EV
    applicants, so changing the economics changes who is even in the pool, and the overlap
    then reports pool churn rather than a change in the allocation decision. Here the
    candidate set, capital units and budget are all held constant, so any change in the
    answer is attributable to the objective alone.
    """
    df = rescore(scored, apr, lgd)
    ev = data_mod.expected_value(df.loc[base.ids], df.loc[base.ids, "p_default"].to_numpy())
    p = pf.PortfolioProblem(ids=base.ids, ev=np.asarray(ev, dtype=float), units=base.units,
                            budget_units=base.budget_units, sex=base.sex,
                            fairness_lambda=0.0, meta=base.meta)
    x = solvers.solve_bruteforce(p).x
    return {i for i, keep in zip(p.ids, x) if keep}


def jaccard(a: set, b: set) -> float:
    return len(a & b) / len(a | b) if (a or b) else 1.0


def main() -> None:
    scored = pd.read_csv(ARTIFACTS / "scored_applicants.csv")
    baseline = {s: selected_ids(scored, BASE_APR, BASE_LGD, s) for s in SEEDS}

    # 1. Confirm the scale invariance empirically rather than only asserting the algebra.
    invariance = []
    for k in (0.5, 2.0, 3.0):
        for s in SEEDS:
            sel = selected_ids(scored, BASE_APR * k, BASE_LGD * k, s)
            invariance.append(jaccard(sel, baseline[s]))
    invariance_holds = bool(np.min(invariance) == 1.0)
    print(f"scale invariance (apr,lgd -> k*apr,k*lgd): min overlap "
          f"{np.min(invariance):.3f} over {len(invariance)} checks -> "
          f"{'CONFIRMED' if invariance_holds else 'VIOLATED'}\n", flush=True)

    # 2. Sensitivity to the one parameter that does matter, measured two ways.
    base_df = rescore(scored, BASE_APR, BASE_LGD)
    base_problems = {s: pf.build_problem(base_df, n=POOL_N, fairness_lambda=0.0, seed=s)
                     for s in SEEDS}
    base_fixed = {s: selected_ids_fixed_pool(scored, base_problems[s], BASE_APR, BASE_LGD)
                  for s in SEEDS}

    rows = []
    for rho in RHOS:
        full, fixed, sizes = [], [], []
        for s in SEEDS:
            sel = selected_ids(scored, BASE_APR, BASE_APR * rho, s)
            full.append(jaccard(sel, baseline[s]))
            sizes.append(len(sel))
            self_ = selected_ids_fixed_pool(scored, base_problems[s], BASE_APR, BASE_APR * rho)
            fixed.append(jaccard(self_, base_fixed[s]))
        rows.append(dict(rho=rho, lgd_at_12pct_apr=BASE_APR * rho,
                         jaccard_mean=float(np.mean(fixed)),
                         jaccard_min=float(np.min(fixed)),
                         jaccard_full_pipeline=float(np.mean(full)),
                         n_funded=float(np.mean(sizes))))
        print(f"  rho={rho:5.1f}  same-pool overlap={np.mean(fixed):.3f}   "
              f"full-pipeline overlap={np.mean(full):.3f}   funded={np.mean(sizes):.1f}",
              flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(ARTIFACTS / "bench_sensitivity.csv", index=False)

    off = df[df.rho != BASE_RHO]
    near = df[(df.rho >= 4.0) & (df.rho <= 6.0) & (df.rho != BASE_RHO)]
    worst = off.loc[off.jaccard_mean.idxmin()]

    meta = {
        "base_apr": BASE_APR, "base_lgd": BASE_LGD, "base_rho": BASE_RHO,
        "scale_invariance_confirmed": invariance_holds,
        "seeds": len(SEEDS),
        "mean_overlap_off_baseline": float(off.jaccard_mean.mean()),
        "mean_overlap_rho_4_to_6": float(near.jaccard_mean.mean()),
        "mean_overlap_full_pipeline": float(off.jaccard_full_pipeline.mean()),
        "worst_overlap": float(worst.jaccard_mean), "worst_at_rho": float(worst.rho),
        "portfolio_is_robust_near_baseline": bool(near.jaccard_mean.mean() >= 0.70),
    }
    (ARTIFACTS / "bench_sensitivity_meta.json").write_text(json.dumps(meta, indent=2))

    print("\n=== SENSITIVITY TO THE INVENTED ECONOMICS ===")
    print(f"Only rho = lgd/apr matters; scale invariance "
          f"{'confirmed' if invariance_holds else 'VIOLATED'} over {len(invariance)} checks.")
    print(f"same-pool overlap, rho in [4,6]:      {meta['mean_overlap_rho_4_to_6']:.3f}")
    print(f"same-pool overlap, full sweep:        {meta['mean_overlap_off_baseline']:.3f}")
    print(f"full-pipeline overlap (pool re-screened): {meta['mean_overlap_full_pipeline']:.3f}")
    print(f"worst case: {meta['worst_overlap']:.3f} at rho={worst.rho:.1f}")
    print("-> stable against plausible mis-pricing near the baseline."
          if meta["portfolio_is_robust_near_baseline"] else
          "-> SENSITIVE even near the baseline; the portfolio is a function of rho and "
          "must be reported as such.")


if __name__ == "__main__":
    main()
