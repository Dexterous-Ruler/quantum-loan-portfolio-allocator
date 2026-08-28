"""Deliverable 2 (the quantum module) and its classical counterparts.

Everything here solves the SAME QUBO, so Deliverable 4 is an apples-to-apples comparison
of optimisers -- not a comparison of two different classifiers.
"""
from __future__ import annotations

import itertools
import time
from dataclasses import dataclass

import numpy as np
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit_aer.primitives import SamplerV2
from qiskit_optimization.algorithms import MinimumEigenOptimizer
from qiskit_optimization.minimum_eigensolvers import QAOA, NumPyMinimumEigensolver
from qiskit_optimization.optimizers import COBYLA
from qiskit_optimization.translators import to_ising

import portfolio as pf


@dataclass
class Solution:
    name: str
    x: np.ndarray
    objective: float
    seconds: float
    feasible: bool
    extra: dict | None = None


def _finish(name: str, x, p: pf.PortfolioProblem, t0: float, extra=None) -> Solution:
    x = np.asarray(x, dtype=int)
    return Solution(name, x, p.objective(x), time.perf_counter() - t0, p.is_feasible(x), extra or {})


# ---------------------------------------------------------------- classical


def solve_bruteforce(p: pf.PortfolioProblem) -> Solution:
    """Exact optimum by enumeration. Ground truth for the approximation ratio.

    Tractable only because we deliberately kept n small (2^12 = 4096). This is the
    honest reference every other solver is scored against.
    """
    t0 = time.perf_counter()
    best_x, best_obj = None, -np.inf
    for bits in itertools.product((0, 1), repeat=p.n):
        x = np.array(bits, dtype=int)
        if not p.is_feasible(x):
            continue
        obj = p.objective(x)
        if obj > best_obj:
            best_obj, best_x = obj, x
    return _finish("Exact (brute force)", best_x, p, t0)


def solve_greedy(p: pf.PortfolioProblem) -> Solution:
    """Classic knapsack heuristic: take loans by descending value-per-unit-capital."""
    t0 = time.perf_counter()
    order = np.argsort(-(p.ev / np.maximum(p.units, 1)))
    x = np.zeros(p.n, dtype=int)
    spent = 0
    for i in order:
        if p.ev[i] <= 0:
            continue
        if spent + p.units[i] <= p.budget_units:
            x[i] = 1
            spent += p.units[i]
    return _finish("Greedy (value/capital)", x, p, t0)


def solve_numpy_eigensolver(p: pf.PortfolioProblem) -> Solution:
    """Exact diagonalisation of the QUBO. Proves the Hamiltonian encodes the right problem."""
    t0 = time.perf_counter()
    qp = pf.to_quadratic_program(p)
    res = MinimumEigenOptimizer(NumPyMinimumEigensolver()).solve(qp)
    return _finish("Exact (QUBO diagonalisation)", res.x, p, t0)


# ---------------------------------------------------------------- quantum


def solve_qaoa(
    p: pf.PortfolioProblem,
    reps: int = 2,
    maxiter: int = 200,
    shots: int = 2048,
    seed: int = 42,
    top_k: int = 5,
) -> Solution:
    """QAOA on the portfolio QUBO.

    Shot-based sampling (not exact statevector expectation) is used on purpose: measurement
    sampling is part of the quantum concept being demonstrated, and it is what produces the
    ranked distribution of near-optimal portfolios used by the demo.
    """
    t0 = time.perf_counter()
    qp = pf.to_quadratic_program(p)

    sampler = SamplerV2(seed=seed, default_shots=shots)
    # Aer's SamplerV2 warns (correctly) that an untranspiled circuit may fail. Supplying an
    # explicit pass manager makes the ansatz target the simulator's real basis gates instead
    # of relying on implicit handling -- and keeps the demo console clean.
    pm = generate_preset_pass_manager(optimization_level=1, backend=AerSimulator())
    qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=maxiter), reps=reps, pass_manager=pm)
    res = MinimumEigenOptimizer(qaoa).solve(qp)

    # A ranked portfolio of feasible near-optimal alternatives, read off the measurement
    # distribution we already paid for. A single MILP optimum cannot provide this.
    alts = []
    for s in sorted(res.samples, key=lambda s: s.probability, reverse=True):
        x = np.asarray(s.x[: p.n], dtype=int)
        if p.is_feasible(x):
            alts.append({"x": x.tolist(), "objective": p.objective(x), "probability": float(s.probability)})
        if len(alts) >= top_k:
            break

    _, offset = to_ising(pf.QuadraticProgramToQubo().convert(qp))
    return _finish(
        f"QAOA (p={reps})",
        np.asarray(res.x[: p.n], dtype=int),
        p,
        t0,
        {"reps": reps, "shots": shots, "maxiter": maxiter, "alternatives": alts, "ising_offset": float(offset)},
    )


def ansatz_stats(p: pf.PortfolioProblem, reps: int = 1) -> dict:
    """Concrete facts about the circuit that actually runs.

    A 14-qubit QAOA diagram is unreadable on a projector, so show the numbers instead:
    qubits, variational parameters, and the two-qubit gate count after transpilation to
    the simulator's real basis. Two-qubit depth is the figure of merit that would decide
    whether this is runnable on hardware.
    """
    from qiskit.circuit.library import QAOAAnsatz

    qubo, _ = pf.qubo_and_qubits(p)
    op, _ = to_ising(qubo)
    ansatz = QAOAAnsatz(cost_operator=op, reps=reps)

    pm = generate_preset_pass_manager(optimization_level=1, backend=AerSimulator())
    transpiled = pm.run(ansatz.decompose(reps=3))
    ops = transpiled.count_ops()
    two_qubit = sum(v for k, v in ops.items() if k in ("cx", "cz", "ecr", "rzz"))

    return {
        "qubits": op.num_qubits,
        "pauli_terms": len(op.paulis),
        "reps": reps,
        "parameters": ansatz.num_parameters,
        "depth": transpiled.depth(),
        "two_qubit_gates": two_qubit,
        "gate_counts": {k: int(v) for k, v in ops.items()},
    }


def hamiltonian_terms(p: pf.PortfolioProblem, top: int = 8):
    """The largest Pauli terms of the cost Hamiltonian, for the 'show your work' slide.

    Being able to point at a specific ZZ coupling and name the two applicants it links is
    the difference between demonstrating a quantum method and invoking one.
    """
    qubo, _ = pf.qubo_and_qubits(p)
    op, offset = to_ising(qubo)
    terms = sorted(
        ({"pauli": str(pl), "coeff": float(np.real(c))} for pl, c in zip(op.paulis, op.coeffs)),
        key=lambda t: -abs(t["coeff"]),
    )
    return terms[:top], float(offset), op.num_qubits
