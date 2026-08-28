"""Charts for the one-page comparison and the demo.

Deliberately plain: no seaborn, no styling beyond what carries information. Every figure
answers one question a judge would ask out loud.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from sklearn.calibration import calibration_curve  # noqa: E402

import portfolio as pf  # noqa: E402
import solvers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
FIGS = ARTIFACTS / "figures"

INK = "#1a1a1a"
QCOL = "#4c6ef5"
CCOL = "#c92a2a"


def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)


def fig_quality() -> Path:
    """Does any QAOA depth actually beat the others? (Answer: no, and the plot shows why.)"""
    q = pd.read_csv(ARTIFACTS / "bench_quality.csv")
    qa = q[q.solver.str.startswith("QAOA")]
    greedy = q[q.solver.str.startswith("Greedy")]["ar"].mean()

    depths = sorted(qa.reps.dropna().unique())
    fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=160)
    rng = np.random.default_rng(0)
    for i, d in enumerate(depths):
        vals = qa[qa.reps == d]["ar"].to_numpy()
        ax.scatter(np.full_like(vals, i) + rng.uniform(-0.11, 0.11, vals.size), vals,
                   s=22, alpha=0.55, color=QCOL, edgecolor="none", zorder=3)
        ax.hlines(vals.mean(), i - 0.28, i + 0.28, color=INK, linewidth=2.2, zorder=4)

    ax.axhline(greedy, color=CCOL, linestyle="--", linewidth=1.4,
               label=f"Greedy heuristic ({greedy:.4f})")
    ax.axhline(1.0, color="#888", linestyle=":", linewidth=1.2, label="Exact optimum")
    ax.set_xticks(range(len(depths)))
    ax.set_xticklabels([f"p={int(d)}" for d in depths])
    ax.set_ylabel("Approximation ratio")
    ax.set_title("Every QAOA run, by circuit depth\nSpread within a depth swamps the gaps between depths",
                 fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False, loc="lower left")
    _style(ax)
    fig.tight_layout()
    out = FIGS / "quality.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_scaling() -> Path:
    """Where does this stop being simulable?"""
    s = pd.read_csv(ARTIFACTS / "bench_scaling.csv")
    fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=160)
    ax.plot(s.qubits, s.qaoa_p1_seconds, "o-", color=QCOL, linewidth=2, label="QAOA p=1")
    ax.plot(s.qubits, s.exact_seconds, "s-", color=CCOL, linewidth=2, label="Exact (brute force)")
    ax.set_yscale("log")
    ax.set_xlabel("Qubits")
    ax.set_ylabel("Wall clock (s, log scale)")
    ax.set_title("The scaling wall\nClassical is 2-3 orders of magnitude faster at every size we can simulate",
                 fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    fig.tight_layout()
    out = FIGS / "scaling.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_fairness(n_seeds: int = 6) -> Path:
    """What does approval-rate parity cost, in money?

    Swept with exact brute force (not QAOA) so the frontier reflects the problem, not
    solver noise -- 2^10 enumeration is milliseconds.
    """
    scored = pd.read_csv(ARTIFACTS / "scored_applicants.csv")
    lambdas = [0, 500, 1000, 2000, 4000, 8000, 16000, 32000, 64000]
    rows = []
    for lam in lambdas:
        profits, gaps = [], []
        for seed in range(n_seeds):
            p = pf.build_problem(scored, n=10, fairness_lambda=float(lam), seed=seed)
            x = solvers.solve_bruteforce(p).x
            profits.append(float(p.ev @ x))
            gaps.append(abs(p.parity_gap(x)))
        rows.append(dict(lam=lam, profit=np.mean(profits), gap=np.mean(gaps)))
    df = pd.DataFrame(rows)
    df.to_csv(ARTIFACTS / "fairness_frontier.csv", index=False)

    fig, ax = plt.subplots(figsize=(6.2, 3.6), dpi=160)
    ax.plot(df.gap * 100, df.profit, "o-", color=QCOL, linewidth=2, zorder=3)
    for _, r in df.iterrows():
        if r.lam in (0, 8000, 64000):
            ax.annotate(f"$\\lambda$={int(r.lam):,}", (r.gap * 100, r.profit),
                        textcoords="offset points", xytext=(8, 6), fontsize=8, color=INK)
    ax.set_xlabel("Approval-rate gap between groups (percentage points)")
    ax.set_ylabel("Expected profit (DM)")
    ax.set_title("The price of parity\nEach point is an optimal portfolio at a different fairness weight",
                 fontsize=10, loc="left")
    _style(ax)
    fig.tight_layout()
    out = FIGS / "fairness.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def fig_calibration() -> Path:
    """Are the probabilities that parameterise the Hamiltonian trustworthy?"""
    scored = pd.read_csv(ARTIFACTS / "scored_applicants.csv")
    te = scored[scored.is_test]
    frac, mean_pred = calibration_curve(te["default"], te["p_default"], n_bins=8, strategy="quantile")

    fig, ax = plt.subplots(figsize=(4.2, 3.6), dpi=160)
    ax.plot([0, 1], [0, 1], ":", color="#888", linewidth=1.2, label="Perfect calibration")
    ax.plot(mean_pred, frac, "o-", color=QCOL, linewidth=2, label="Calibrated GBM")
    ax.set_xlabel("Predicted P(default)")
    ax.set_ylabel("Observed default rate")
    ax.set_title("Calibration\nThe optimiser multiplies these by cash", fontsize=10, loc="left")
    ax.legend(fontsize=8, frameon=False)
    _style(ax)
    fig.tight_layout()
    out = FIGS / "calibration.png"
    fig.savefig(out)
    plt.close(fig)
    return out


def main() -> None:
    FIGS.mkdir(parents=True, exist_ok=True)
    for fn in (fig_quality, fig_scaling, fig_fairness, fig_calibration):
        print("wrote", fn().relative_to(ROOT))


if __name__ == "__main__":
    main()
