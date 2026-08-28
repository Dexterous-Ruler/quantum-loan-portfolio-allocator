"""Deliverable 4 -- the evidence behind the one-page comparison.

Produces two tables:
  A. Solution quality vs QAOA depth, averaged over independent instances, with spread.
     One lucky run is not a result; this reports min/mean over seeds.
  B. The scaling wall -- qubit count and wall-clock as the pool grows, and where
     statevector simulation stops being possible on a laptop.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import numpy as np
import pandas as pd

import portfolio as pf
import solvers

ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"
SEEDS = list(range(8))
DEPTHS = [1, 2, 3]
POOL_N = 10
# QAOA is stochastic in two independent ways: which instance you drew, and which random
# seed the sampler/optimiser started from. Running one QAOA seed per instance confounds
# them -- and it is enough to flip the apparent ranking of depths between runs, which is
# exactly the trap this table exists to avoid. Repeat each (instance, depth) cell.
QAOA_REPEATS = 3


def quality_table(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for seed in SEEDS:
        p = pf.build_problem(scored, n=POOL_N, fairness_lambda=0.0, seed=seed)
        _, nq = pf.qubo_and_qubits(p)

        exact = solvers.solve_bruteforce(p)
        greedy = solvers.solve_greedy(p)
        rows.append(dict(seed=seed, qaoa_seed=None, solver="Exact (brute force)", reps=None, qubits=nq,
                         objective=exact.objective, ar=1.0, seconds=exact.seconds, hit=True))
        rows.append(dict(seed=seed, qaoa_seed=None, solver="Greedy heuristic", reps=None, qubits=nq,
                         objective=greedy.objective, ar=greedy.objective / exact.objective,
                         seconds=greedy.seconds, hit=abs(greedy.objective - exact.objective) < 1e-6))

        for reps in DEPTHS:
            for r in range(QAOA_REPEATS):
                qseed = 1000 + 97 * seed + r
                q = solvers.solve_qaoa(p, reps=reps, seed=qseed)
                ar = q.objective / exact.objective
                rows.append(dict(seed=seed, qaoa_seed=qseed, solver=f"QAOA p={reps}", reps=reps, qubits=nq,
                                 objective=q.objective, ar=ar, seconds=q.seconds,
                                 hit=abs(q.objective - exact.objective) < 1e-6))
                print(f"  seed={seed} p={reps} rep={r} AR={ar:.4f} t={q.seconds:.1f}s", flush=True)
    return pd.DataFrame(rows)


def scaling_table(scored: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for n in (6, 8, 10, 12):
        p = pf.build_problem(scored, n=n, fairness_lambda=0.0, seed=0)
        _, nq = pf.qubo_and_qubits(p)
        t0 = time.perf_counter()
        solvers.solve_qaoa(p, reps=1, seed=7)
        qaoa_s = time.perf_counter() - t0
        exact = solvers.solve_bruteforce(p)
        rows.append(dict(pool_n=n, qubits=nq,
                         statevector_mb=(2 ** nq) * 16 / 1e6,
                         qaoa_p1_seconds=qaoa_s, exact_seconds=exact.seconds))
        print(f"  n={n} qubits={nq} qaoa={qaoa_s:.1f}s exact={exact.seconds:.3f}s", flush=True)
    return pd.DataFrame(rows)


def fairness_table(scored: pd.DataFrame) -> pd.DataFrame:
    """What the fairness penalty costs in profit and buys in approval-rate parity."""
    rows = []
    for seed in SEEDS[:5]:
        for lam in (0.0, 2000.0, 20000.0):
            p = pf.build_problem(scored, n=POOL_N, fairness_lambda=lam, seed=seed)
            s = solvers.solve_bruteforce(p)
            rows.append(dict(seed=seed, fairness_lambda=lam,
                             profit=float(p.ev @ s.x), parity_gap=p.parity_gap(s.x),
                             n_funded=int(s.x.sum())))
    return pd.DataFrame(rows)


def main():
    scored = pd.read_csv(ARTIFACTS / "scored_applicants.csv")
    ARTIFACTS.mkdir(exist_ok=True)

    print("[1/3] quality vs depth", flush=True)
    q = quality_table(scored)
    q.to_csv(ARTIFACTS / "bench_quality.csv", index=False)

    print("[2/3] scaling", flush=True)
    s = scaling_table(scored)
    s.to_csv(ARTIFACTS / "bench_scaling.csv", index=False)

    print("[3/3] fairness", flush=True)
    f = fairness_table(scored)
    f.to_csv(ARTIFACTS / "bench_fairness.csv", index=False)

    summary = (
        q[q.solver.str.startswith(("QAOA", "Greedy"))]
        .groupby("solver")
        .agg(ar_mean=("ar", "mean"), ar_min=("ar", "min"), ar_std=("ar", "std"),
             hit_rate=("hit", "mean"), seconds=("seconds", "mean"))
        .reset_index()
    )
    summary.to_csv(ARTIFACTS / "bench_summary.csv", index=False)
    print("\n=== SUMMARY ===")
    print(summary.to_string(index=False))

    # Is the depth ranking real, or is it noise? Compare the spread BETWEEN depth means
    # against the typical spread WITHIN a single (instance, depth) cell across QAOA seeds.
    # If within >= between, no depth is meaningfully best and saying one is would be a lie.
    qonly = q[q.solver.str.startswith("QAOA")]
    within = qonly.groupby(["seed", "solver"])["ar"].std().mean()
    between = qonly.groupby("solver")["ar"].mean().std()
    stability = {
        "within_cell_ar_std": float(within),
        "between_depth_ar_std": float(between),
        "depth_ranking_is_noise": bool(within >= between),
    }
    (ARTIFACTS / "bench_stability.json").write_text(json.dumps(stability, indent=2))
    print("\n=== STABILITY ===")
    print(f"  spread within one (instance,depth) across QAOA seeds: {within:.4f}")
    print(f"  spread between depth means:                           {between:.4f}")
    print(f"  -> depth ranking is noise: {stability['depth_ranking_is_noise']}")

    (ARTIFACTS / "bench_meta.json").write_text(json.dumps(
        {"seeds": len(SEEDS), "depths": DEPTHS, "pool_n": POOL_N, "shots": 2048,
         "maxiter": 200, "qaoa_repeats": QAOA_REPEATS}, indent=2))


if __name__ == "__main__":
    main()
