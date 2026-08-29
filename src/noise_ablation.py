"""How much gate error can this circuit absorb before the answer is worthless?

The brief scopes us to a simulator, so we never touch hardware. But "would this run on a
real device?" is the obvious follow-up question, and it has a measurable answer: sweep a
depolarizing two-qubit gate error and watch the approximation ratio fall.

Sized deliberately small. Noisy simulation is ~24x slower than noiseless (density-matrix
style sampling rather than pure statevector), so this uses 12 qubits and p=1.

    python src/noise_ablation.py        # ~50 minutes

Seed count is set from the measured noise floor: a 3-seed pilot could not separate the noise
levels from seed-to-seed scatter and reported the sweep as inconclusive, with an estimate of
~8 seeds per level needed. We run 12.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import portfolio as pf
import solvers

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"

POOL_N = 8          # 12 qubits
REPS = 1
SEEDS = list(range(12))
# 2-qubit depolarizing error rates. Current superconducting devices sit around 5e-3 to 1e-2,
# so this brackets the real hardware regime on both sides.
ERROR_RATES = [None, 0.001, 0.005, 0.01, 0.02]


def main(summarize_only: bool = False) -> None:
    if summarize_only:
        # Re-derive the summary and meta from an existing sweep. The sweep costs ~17
        # minutes; changing how we analyse it should not.
        summarize(pd.read_csv(ARTIFACTS / "bench_noise.csv"))
        return

    scored = pd.read_csv(ARTIFACTS / "scored_applicants.csv")
    rows = []

    for seed in SEEDS:
        p = pf.build_problem(scored, n=POOL_N, fairness_lambda=0.0, seed=seed)
        _, nq = pf.qubo_and_qubits(p)
        exact = solvers.solve_bruteforce(p)

        for err in ERROR_RATES:
            s = solvers.solve_qaoa(p, reps=REPS, seed=1000 + seed, two_qubit_error=err)
            ar = s.objective / exact.objective
            # `ar_dist` is the metric that actually responds to noise. `ar` (best of
            # `shots` samples) does not -- see the note in solvers.solve_qaoa.
            ar_dist = s.extra["expected_objective"] / exact.objective
            rows.append(dict(
                seed=seed, qubits=nq,
                two_qubit_error=0.0 if err is None else err,
                noiseless=err is None,
                ar=ar, ar_dist=ar_dist,
                feasible_probability=s.extra["feasible_probability"],
                seconds=s.seconds, feasible=bool(s.feasible),
                hit=abs(s.objective - exact.objective) < 1e-6,
            ))
            print(f"  seed={seed} err={str(err):>6} AR_best={ar:.4f} AR_dist={ar_dist:.4f} "
                  f"P(feas)={s.extra['feasible_probability']:.3f} t={s.seconds:.1f}s", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(ARTIFACTS / "bench_noise.csv", index=False)
    summarize(df)


def summarize(df: pd.DataFrame) -> None:
    summary = (
        df.groupby("two_qubit_error")
        .agg(ar_best_mean=("ar", "mean"), ar_dist_mean=("ar_dist", "mean"),
             ar_dist_min=("ar_dist", "min"),
             feas_prob=("feasible_probability", "mean"),
             hit_rate=("hit", "mean"), seconds=("seconds", "mean"))
        .reset_index()
    )
    summary.to_csv(ARTIFACTS / "bench_noise_summary.csv", index=False)

    clean_best = float(summary[summary.two_qubit_error == 0.0]["ar_best_mean"].iloc[0])
    clean_dist = float(summary[summary.two_qubit_error == 0.0]["ar_dist_mean"].iloc[0])
    worst_dist = float(summary["ar_dist_mean"].min())

    # Does best-of-shots actually respond to noise? Range across error rates tells us.
    best_range = float(summary["ar_best_mean"].max() - summary["ar_best_mean"].min())
    dist_range = float(summary["ar_dist_mean"].max() - summary["ar_dist_mean"].min())

    # Hold this claim to the same standard as the depth ranking: a trend across error
    # levels only means something if it is larger than the scatter within a level.
    within = float(df.groupby("two_qubit_error")["ar_dist"].std().mean())
    between = float(summary["ar_dist_mean"].std())
    trend_is_real = between > within

    # If the trend is buried, say how many seeds per level would be needed to dig it out:
    # resolve `between` at roughly 2 standard errors, i.e. within/sqrt(n) < between/2.
    seeds_needed = int(np.ceil((2.0 * within / between) ** 2)) if between > 0 else None
    hours_needed = (
        seeds_needed * len(ERROR_RATES) * float(summary["seconds"].mean()) / 3600.0
        if seeds_needed else None
    )

    json.dump(
        {
            "noiseless_ar_best": clean_best,
            "noiseless_ar_dist": clean_dist,
            "worst_ar_dist": worst_dist,
            "ar_best_range_across_noise": best_range,
            "ar_dist_range_across_noise": dist_range,
            "best_of_shots_is_noise_blind": best_range < dist_range,
            "ar_dist_within_level_std": within,
            "ar_dist_between_level_std": between,
            "noise_trend_exceeds_noise_floor": bool(trend_is_real),
            "seeds_per_level_needed_to_resolve": seeds_needed,
            "hours_needed_to_resolve": hours_needed,
            "pool_n": POOL_N, "reps": REPS, "seeds": len(SEEDS),
            "shots": 2048,
        },
        open(ARTIFACTS / "bench_noise_meta.json", "w"), indent=2,
    )

    print("\n=== NOISE ABLATION ===")
    print(summary.to_string(index=False))
    print(f"\nbest-of-{2048}-shots AR varies by {best_range:.4f} across the noise sweep")
    print(f"distribution AR varies by {dist_range:.4f}")
    print("-> best-of-shots is noise-blind at this size; the distribution metric is not."
          if best_range < dist_range else
          "-> both metrics respond to noise.")
    print(f"\nscatter WITHIN a noise level: {within:.4f} | spread BETWEEN levels: {between:.4f}")
    if trend_is_real:
        print("-> the noise trend exceeds its own noise floor.")
    else:
        print("-> WARNING: the trend does NOT exceed within-level scatter; INCONCLUSIVE.")
        print(f"   resolving it would need ~{seeds_needed} seeds per level "
              f"(~{hours_needed:.0f} h of noisy simulation).")


if __name__ == "__main__":
    import sys

    main(summarize_only="--summarize-only" in sys.argv)
