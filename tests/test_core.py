"""Correctness tests for the data, economics, QUBO mapping, and solvers.

Fast by default: the QAOA tests are marked `slow` because each solve is 4-13 s.

    pytest tests -q                 # ~20 s, skips QAOA
    pytest tests -q -m slow         # includes the quantum solver
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import data as data_mod  # noqa: E402
import portfolio as pf  # noqa: E402
import solvers  # noqa: E402

SCORED = ROOT / "artifacts" / "scored_applicants.csv"


@pytest.fixture(scope="session")
def scored() -> pd.DataFrame:
    if not SCORED.exists():
        pytest.skip("run src/ai_model.py first to produce artifacts/scored_applicants.csv")
    return pd.read_csv(SCORED)


@pytest.fixture(scope="session")
def problem(scored):
    return pf.build_problem(scored, n=10, fairness_lambda=0.0, seed=0)


# ---------------------------------------------------------------- data


def test_dataset_shape_and_target():
    df = data_mod.load()
    assert len(df) == 1000
    assert set(df["default"].unique()) == {0, 1}
    # The documented base rate for German Credit is exactly 30% bad.
    assert df["default"].mean() == pytest.approx(0.30)
    assert set(df["sex"].unique()) == {"male", "female"}


def test_protected_attribute_excluded_from_features():
    df = data_mod.add_loan_economics(data_mod.load())
    X, _ = data_mod.xy(df)
    assert "sex" not in X.columns
    assert "personal_status_sex" not in X.columns
    # Leakage guard: the economics columns are derived from the target-adjacent amount
    # and must not be fed back in as features.
    for leak in ("principal", "interest_if_repaid", "loss_if_default"):
        assert leak not in X.columns


def test_expected_value_signs():
    """A certain repayment earns interest; a certain default loses LGD x principal."""
    df = data_mod.add_loan_economics(data_mod.load()).head(5)
    ev_safe = data_mod.expected_value(df, np.zeros(5))
    ev_doomed = data_mod.expected_value(df, np.ones(5))
    assert np.all(ev_safe > 0)
    assert np.all(ev_doomed < 0)
    assert ev_safe == pytest.approx(df["interest_if_repaid"].to_numpy())
    assert ev_doomed == pytest.approx(-df["loss_if_default"].to_numpy())


# ---------------------------------------------------------------- QUBO mapping


@pytest.mark.parametrize("n,expected_qubits", [(6, 10), (8, 12), (10, 14), (12, 16)])
def test_qubit_count_is_stable(scored, n, expected_qubits):
    """Qubit count drives everything about feasibility -- pin it against regressions."""
    p = pf.build_problem(scored, n=n, fairness_lambda=0.0, seed=0)
    _, nq = pf.qubo_and_qubits(p)
    assert nq == expected_qubits


def test_fairness_penalty_costs_no_qubits(scored):
    plain = pf.build_problem(scored, n=10, fairness_lambda=0.0, seed=0)
    fair = pf.build_problem(scored, n=10, fairness_lambda=20000.0, seed=0)
    assert pf.qubo_and_qubits(plain)[1] == pf.qubo_and_qubits(fair)[1]


def test_fairness_penalty_creates_quadratic_terms(scored):
    """Without fairness the objective is linear; with it, applicants couple."""
    plain = pf.to_quadratic_program(pf.build_problem(scored, n=10, fairness_lambda=0.0, seed=0))
    fair = pf.to_quadratic_program(pf.build_problem(scored, n=10, fairness_lambda=20000.0, seed=0))
    assert len(plain.objective.quadratic.to_dict()) == 0
    assert len(fair.objective.quadratic.to_dict()) > 0


def test_objective_matches_manual_computation(problem):
    x = np.zeros(problem.n, dtype=int)
    x[:3] = 1
    assert problem.objective(x) == pytest.approx(float(problem.ev[:3].sum()))


def test_parity_gap_bounds(problem):
    assert problem.parity_gap(np.ones(problem.n)) == pytest.approx(0.0)
    assert problem.parity_gap(np.zeros(problem.n)) == pytest.approx(0.0)
    assert -1.0 <= problem.parity_gap(np.array([1, 0] * (problem.n // 2))) <= 1.0


# ---------------------------------------------------------------- solvers


def test_bruteforce_matches_qubo_diagonalisation(problem):
    """The QUBO must encode the same problem the brute force enumerates.

    This is the single most important test here: if the converter's penalty weights were
    wrong, these two would disagree and every downstream number would be meaningless.
    """
    brute = solvers.solve_bruteforce(problem)
    eig = solvers.solve_numpy_eigensolver(problem)
    assert brute.objective == pytest.approx(eig.objective)
    assert np.array_equal(brute.x, eig.x)


def test_all_classical_solutions_respect_the_budget(scored):
    for seed in range(4):
        p = pf.build_problem(scored, n=10, fairness_lambda=0.0, seed=seed)
        for s in (solvers.solve_bruteforce(p), solvers.solve_greedy(p)):
            assert s.feasible, f"{s.name} broke the budget on seed {seed}"
            assert int(p.units @ s.x) <= p.budget_units


def test_greedy_never_beats_the_exact_optimum(scored):
    for seed in range(4):
        p = pf.build_problem(scored, n=10, fairness_lambda=0.0, seed=seed)
        assert solvers.solve_greedy(p).objective <= solvers.solve_bruteforce(p).objective + 1e-9


def test_fairness_penalty_actually_narrows_the_gap(scored):
    """The headline fairness claim, as an assertion rather than a chart."""
    gaps = []
    for lam in (0.0, 64000.0):
        per_seed = []
        for seed in range(5):
            p = pf.build_problem(scored, n=10, fairness_lambda=lam, seed=seed)
            per_seed.append(abs(p.parity_gap(solvers.solve_bruteforce(p).x)))
        gaps.append(np.mean(per_seed))
    assert gaps[1] < gaps[0], f"penalty did not reduce parity gap: {gaps}"


def test_hamiltonian_is_well_formed(problem):
    terms, offset, nq = solvers.hamiltonian_terms(problem, top=5)
    assert nq == 14
    assert len(terms) == 5
    assert np.isfinite(offset)
    assert all(len(t["pauli"]) == nq for t in terms)


def test_portfolio_depends_only_on_lgd_over_apr(scored):
    """Scaling APR and LGD together must not change the chosen portfolio.

    EV_i = A_i * APR * [(1-p_i)*d_i/12 - p_i*(LGD/APR)], so scaling both by k scales every
    EV by k, and a knapsack's argmax is invariant under positive scaling. This pins the
    property that lets us report one free parameter (rho = LGD/APR) instead of two invented
    numbers -- see DELIVERABLE_4.md section B3.
    """
    import sensitivity as sens

    for seed in range(3):
        base = sens.selected_ids(scored, sens.BASE_APR, sens.BASE_LGD, seed)
        for k in (0.5, 2.0, 3.0):
            scaled = sens.selected_ids(scored, sens.BASE_APR * k, sens.BASE_LGD * k, seed)
            assert scaled == base, f"scaling by {k} changed the portfolio on seed {seed}"


# ---------------------------------------------------------------- quantum (slow)


@pytest.mark.slow
def test_qaoa_returns_a_feasible_portfolio(problem):
    s = solvers.solve_qaoa(problem, reps=1, seed=42)
    assert s.feasible
    assert s.x.shape == (problem.n,)
    assert set(np.unique(s.x)) <= {0, 1}


@pytest.mark.slow
def test_qaoa_is_within_a_sane_margin_of_optimal(problem):
    """Loose bound on purpose. QAOA is stochastic; a tight threshold here would be a
    flaky test, and the benchmark -- not this suite -- is where quality is measured."""
    exact = solvers.solve_bruteforce(problem)
    s = solvers.solve_qaoa(problem, reps=1, seed=42)
    assert s.objective / exact.objective > 0.70


@pytest.mark.slow
def test_qaoa_alternatives_are_feasible_and_ranked(problem):
    s = solvers.solve_qaoa(problem, reps=1, seed=42, top_k=5)
    alts = s.extra["alternatives"]
    assert alts, "expected at least one feasible sampled portfolio"
    probs = [a["probability"] for a in alts]
    assert probs == sorted(probs, reverse=True)
    for a in alts:
        assert problem.is_feasible(np.array(a["x"]))
