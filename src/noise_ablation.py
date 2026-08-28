"""How much gate error can this circuit absorb before the answer is worthless?

The brief scopes us to a simulator, so we never touch hardware. But "would this run on a
real device?" is the obvious follow-up question, and it has a measurable answer: sweep a
depolarizing two-qubit gate error and watch the approximation ratio fall.

Sized deliberately small. Noisy simulation is ~24x slower than noiseless (density-matrix
style sampling rather than pure statevector), so this uses 12 qubits and p=1.

    python src/noise_ablation.py        # ~17 minutes
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
SEEDS = [0, 1, 2]
# 2-qubit depolarizing error rates. Current superconducting devices sit around 5e-3 to 1e-2,
# so this brackets the real hardware regime on both sides.
ERROR_RATES = [None, 0.001, 0.005, 0.01, 0.02]


def main() -> None:
    scored = pd.read_csv(ARTIFACTS / "scored_applicants.csv")
    rows = []

    for seed in SEEDS:
        p = pf.build_problem(scored, n=POOL_N, fairness_lambda=0.0, seed=seed)
        _, nq = pf.qubo_and_qubits(p)
        exact = solvers.solve_bruteforce(p)

        for err in ERROR_RATES:
            s = solvers.solve_qaoa(p, reps=REPS, seed=1000 + seed, two_qubit_error=err)
            ar = s.objective / exact.objective
            rows.append(dict(
                seed=seed, qubits=nq,
                two_qubit_error=0.0 if err is None else err,
                noiseless=err is None,
                ar=ar, seconds=s.seconds, feasible=bool(s.feasible),
                hit=abs(s.objective - exact.objective) < 1e-6,
            ))
            print(f"  seed={seed} err={str(err):>6} AR={ar:.4f} t={s.seconds:.1f}s", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(ARTIFACTS / "bench_noise.csv", index=False)

    summary = (
        df.groupby("two_qubit_error")
        .agg(ar_mean=("ar", "mean"), ar_min=("ar", "min"),
             hit_rate=("hit", "mean"), seconds=("seconds", "mean"))
        .reset_index()
    )
    summary.to_csv(ARTIFACTS / "bench_noise_summary.csv", index=False)

    clean = summary[summary.two_qubit_error == 0.0]["ar_mean"].iloc[0]
    # The error rate at which the mean approximation ratio drops below the greedy heuristic
    # is the honest answer to "is this hardware-ready?".
    try:
        greedy_ar = pd.read_csv(ARTIFACTS / "bench_summary.csv")
        greedy_ar = float(greedy_ar[greedy_ar.solver.str.startswith("Greedy")]["ar_mean"].iloc[0])
    except Exception:
        greedy_ar = float("nan")

    below = summary[(summary.two_qubit_error > 0) & (summary.ar_mean < greedy_ar)]
    breakeven = float(below["two_qubit_error"].min()) if len(below) else None

    json.dump(
        {"noiseless_ar": float(clean), "greedy_ar": greedy_ar,
         "error_where_qaoa_falls_below_greedy": breakeven,
         "pool_n": POOL_N, "reps": REPS, "seeds": len(SEEDS)},
        open(ARTIFACTS / "bench_noise_meta.json", "w"), indent=2,
    )

    print("\n=== NOISE ABLATION ===")
    print(summary.to_string(index=False))
    print(f"\nnoiseless AR {clean:.4f} | greedy AR {greedy_ar:.4f}")
    print(f"QAOA falls below the classical heuristic at 2-qubit error >= {breakeven}")


if __name__ == "__main__":
    main()
