"""The optimisation problem: allocate a fixed capital budget across loan applications.

This is where the AI model and the quantum module sit in SERIES rather than side by side.
The classifier's calibrated P(default) sets the expected-value coefficients of the
objective, i.e. the ML output literally parameterises the cost Hamiltonian.

Formulation
-----------
Decision variables:  x_i in {0,1}, "fund applicant i".

    maximise    sum_i  EV_i * x_i                       (risk-adjusted profit)
                - lambda * parity_gap(x)^2              (fairness penalty)
    subject to  sum_i  units_i * x_i  <=  budget_units  (capital budget)

Two modelling choices worth defending to a judge:

1. The budget is an INEQUALITY. `QuadraticProgramToQubo` handles it by introducing an
   integer slack variable and binary-expanding it, which costs ceil(log2(budget+1))
   extra qubits. That is why we discretise capital into coarse units -- it is the
   single lever that controls qubit count.

2. The fairness term is a SOFT PENALTY, not a constraint. This is deliberate and it
   costs zero extra qubits. It also changes the physics: a plain knapsack objective is
   linear, so all the quadratic structure would come from the constraint penalty alone.
   The squared parity gap introduces genuine ZZ couplings between applicants of opposite
   groups -- pairs of applicants now interact in the Hamiltonian. The problem is
   quadratic by construction, not by accident.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from qiskit_optimization import QuadraticProgram
from qiskit_optimization.converters import QuadraticProgramToQubo

UNIT_SIZE = 1000.0  # DM of principal per capital "unit"
MAX_UNITS = 6


@dataclass
class PortfolioProblem:
    """A concrete, sized instance of the allocation problem."""

    ids: list[int]
    ev: np.ndarray                # expected value per loan (DM)
    units: np.ndarray             # discretised principal per loan
    budget_units: int
    sex: np.ndarray               # protected attribute, for the fairness term
    fairness_lambda: float = 0.0
    meta: pd.DataFrame | None = field(default=None, repr=False)

    @property
    def n(self) -> int:
        return len(self.ids)

    def parity_gap(self, x: np.ndarray) -> float:
        """Approval-rate difference between the two groups under selection x."""
        x = np.asarray(x, dtype=float)
        f = self.sex == "female"
        m = ~f
        rf = x[f].sum() / max(f.sum(), 1)
        rm = x[m].sum() / max(m.sum(), 1)
        return float(rf - rm)

    def objective(self, x: np.ndarray) -> float:
        """The true maximisation objective (profit minus fairness penalty)."""
        x = np.asarray(x, dtype=float)
        return float(self.ev @ x - self.fairness_lambda * self.parity_gap(x) ** 2)

    def is_feasible(self, x: np.ndarray) -> bool:
        return float(np.asarray(x, dtype=float) @ self.units) <= self.budget_units + 1e-9


def build_problem(
    scored: pd.DataFrame,
    n: int = 10,
    budget_fraction: float = 0.45,
    fairness_lambda: float = 0.0,
    seed: int = 0,
    positive_ev_only: bool = True,
) -> PortfolioProblem:
    """Draw a candidate pool and size the budget so the constraint actually binds.

    `positive_ev_only` models a bank that has already screened out applications with
    negative risk-adjusted value; the optimiser's job is allocating scarce capital
    among the viable ones. Without it most variables are trivially zero and the
    instance is far easier than it looks.
    """
    pool = scored[scored["is_test"]].dropna(subset=["expected_value"])
    if positive_ev_only:
        pool = pool[pool["expected_value"] > 0]
    if len(pool) < n:
        raise ValueError(f"candidate pool has only {len(pool)} rows, need {n}")

    rng = np.random.default_rng(seed)
    take = rng.choice(len(pool), size=n, replace=False)
    sel = pool.iloc[take]

    units = np.clip(np.ceil(sel["principal"].to_numpy() / UNIT_SIZE), 1, MAX_UNITS).astype(int)
    budget_units = max(2, int(round(budget_fraction * units.sum())))

    return PortfolioProblem(
        ids=[int(i) for i in sel.index],
        ev=sel["expected_value"].to_numpy(dtype=float),
        units=units,
        budget_units=budget_units,
        sex=sel["sex"].to_numpy(),
        fairness_lambda=fairness_lambda,
        meta=sel,
    )


def to_quadratic_program(p: PortfolioProblem) -> QuadraticProgram:
    """Express the problem as a Qiskit QuadraticProgram (minimisation form)."""
    qp = QuadraticProgram("loan_portfolio")
    for i in range(p.n):
        qp.binary_var(name=f"x{i}")

    # Minimise negative profit.
    linear = {f"x{i}": -float(p.ev[i]) for i in range(p.n)}
    quadratic: dict[tuple[str, str], float] = {}

    if p.fairness_lambda > 0:
        # gap(x) = sum_i c_i x_i  with c_i = +1/n_f for female, -1/n_m for male.
        # lambda * gap^2 expands to lambda * sum_ij c_i c_j x_i x_j  (x_i^2 = x_i for binaries).
        f = p.sex == "female"
        n_f, n_m = max(f.sum(), 1), max((~f).sum(), 1)
        c = np.where(f, 1.0 / n_f, -1.0 / n_m)
        for i in range(p.n):
            for j in range(i, p.n):
                coeff = p.fairness_lambda * c[i] * c[j] * (1.0 if i == j else 2.0)
                if i == j:
                    linear[f"x{i}"] += coeff
                elif abs(coeff) > 1e-12:
                    quadratic[(f"x{i}", f"x{j}")] = coeff

    qp.minimize(linear=linear, quadratic=quadratic)
    qp.linear_constraint(
        linear={f"x{i}": int(p.units[i]) for i in range(p.n)},
        sense="<=",
        rhs=int(p.budget_units),
        name="capital_budget",
    )
    return qp


def qubo_and_qubits(p: PortfolioProblem) -> tuple[QuadraticProgram, int]:
    """Convert to unconstrained QUBO and report the qubit count that actually matters."""
    qp = to_quadratic_program(p)
    qubo = QuadraticProgramToQubo().convert(qp)
    return qubo, qubo.get_num_binary_vars()
