"""Does CVaR aggregation actually help on this problem?

Barkoutsos et al. (Quantum 4, 256 (2020)) report that aggregating QAOA samples by the
Conditional Value-at-Risk of the best alpha-fraction, rather than by their mean, converges
faster and to better solutions on every combinatorial problem they tested. It is a one-
parameter change and it is what the strongest comparable projects on GitHub use.

A four-seed pilot here showed differences of ~0.01 in approximation ratio, non-monotonic in
alpha -- which is the same size as the seed-to-seed scatter we already measured for circuit
depth. So this script applies the same standard used everywhere else in the repo: run enough
seeds to establish a noise floor, and only claim an effect that clears it.

    python src/cvar_ablation.py       # ~8 minutes
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import portfolio as pf
import solvers

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

POOL_N = 10
REPS = 1
SEEDS = list(range(8))
QAOA_REPEATS = 3
# None = plain mean aggregation (the qiskit default). Lower alpha = more aggressive CVaR.
ALPHAS = [None, 0.5, 0.25, 0.1]


def label(a: float | None) -> str:
    return "mean (default)" if a is None else f"CVaR alpha={a}"


def main() -> None:
    scored = pd.read_csv(ARTIFACTS / "scored_applicants.csv")
    rows = []

    for seed in SEEDS:
        p = pf.build_problem(scored, n=POOL_N, fairness_lambda=0.0, seed=seed)
        exact = solvers.solve_bruteforce(p)
        for alpha in ALPHAS:
            for r in range(QAOA_REPEATS):
                s = solvers.solve_qaoa(p, reps=REPS, seed=1000 + 97 * seed + r,
                                       aggregation=alpha)
                ar = s.objective / exact.objective
                rows.append(dict(seed=seed, qaoa_seed=1000 + 97 * seed + r,
                                 alpha=-1.0 if alpha is None else alpha,
                                 label=label(alpha), ar=ar, seconds=s.seconds,
                                 hit=abs(s.objective - exact.objective) < 1e-6))
            print(f"  seed={seed} {label(alpha):<16} "
                  f"AR={np.mean([x['ar'] for x in rows[-QAOA_REPEATS:]]):.4f}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(ARTIFACTS / "bench_cvar.csv", index=False)

    summary = (
        df.groupby("label")
        .agg(ar_mean=("ar", "mean"), ar_min=("ar", "min"), ar_std=("ar", "std"),
             hit_rate=("hit", "mean"), seconds=("seconds", "mean"))
        .reset_index()
    )
    summary.to_csv(ARTIFACTS / "bench_cvar_summary.csv", index=False)

    # Same noise-floor test as the depth ranking: is the spread between settings larger
    # than the scatter within one (instance, setting) cell?
    within = float(df.groupby(["seed", "label"])["ar"].std().mean())
    between = float(summary["ar_mean"].std())
    real = between > within

    baseline = summary[summary.label == "mean (default)"].iloc[0]
    best = summary.loc[summary.ar_mean.idxmax()]
    delta = float(best.ar_mean - baseline.ar_mean)

    meta = {
        "baseline_ar": float(baseline.ar_mean), "baseline_hit": float(baseline.hit_rate),
        "best_label": str(best.label), "best_ar": float(best.ar_mean),
        "best_hit": float(best.hit_rate), "improvement": delta,
        "within_cell_std": within, "between_setting_std": between,
        "effect_exceeds_noise_floor": bool(real),
        "seeds": len(SEEDS), "repeats": QAOA_REPEATS,
        "runs_per_setting": len(SEEDS) * QAOA_REPEATS,
    }
    (ARTIFACTS / "bench_cvar_meta.json").write_text(json.dumps(meta, indent=2))

    print("\n=== CVaR ABLATION ===")
    print(summary.to_string(index=False))
    print(f"\nbest: {best.label} at AR {best.ar_mean:.4f} "
          f"vs default {baseline.ar_mean:.4f}  (delta {delta:+.4f})")
    print(f"scatter WITHIN a cell: {within:.4f} | spread BETWEEN settings: {between:.4f}")
    print("-> the effect clears its own noise floor." if real else
          "-> INCONCLUSIVE: the difference between aggregation settings is smaller than "
          "the seed-to-seed scatter. Keep the default and say why.")


if __name__ == "__main__":
    main()
