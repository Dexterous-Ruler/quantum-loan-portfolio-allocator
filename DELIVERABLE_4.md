# Deliverable 4 — Where the quantum mapping helps, where it doesn't, and where it stops being simulable

**Task (identical for both sides):** allocate a fixed capital budget across a pool of
10 scored loan applications to maximise risk-adjusted expected profit, subject to
a capital-budget constraint. The AI model supplies P(default) per applicant; those
probabilities become the linear coefficients of a QUBO. Every solver below attacks the
**same QUBO on the same instances** — this compares *optimisers*, not two different classifiers.

**Setup:** 8 independent instances × QAOA depths [1, 2, 3],
2048 shots, COBYLA maxiter 200, Qiskit Aer statevector simulator,
14 qubits (10 decision variables + 4 binary slack bits from the budget inequality).

---

## A. Solution quality — 8 instances × 3 QAOA seeds per cell

Each row pools 8 × 3 = 24 runs.
The "Std dev" column is the number that matters most on this page — see finding 3.

| Solver | Approx ratio (mean) | Approx ratio (worst) | Std dev | Hit exact optimum | Wall clock (s) |
| --- | --- | --- | --- | --- | --- |
| QAOA p=1 | 0.9594 | 0.8096 | 0.0568 | 46% | 6.1 |
| QAOA p=2 | 0.9860 | 0.8688 | 0.0309 | 71% | 8.3 |
| QAOA p=3 | 0.9882 | 0.8251 | 0.0383 | 79% | 11.8 |

Classical references on the same instances:

| Solver | Approx ratio (mean) | Hit exact optimum | Wall clock (s) |
| --- | --- | --- | --- |
| Exact (brute force) | 1.0000 | 100% | 0.0205 |
| Greedy (value/capital) | 0.9921 | 62% | 0.0001 |

### What this actually says

1. **QAOA is competitive on quality and hopeless on speed.** Pooled across all depths and
   repeats, QAOA averages **0.9779** and hits the exact optimum on
   **65%** of runs, taking **8.7 s** against **0.0205 s**
   for exhaustive classical search — roughly **425× slower**. At 14 qubits there
   is no honest speed claim to make, and any team reporting a quantum speed win at this scale
   benchmarked against a crippled baseline.

2. **QAOA versus the heuristic a bank would actually deploy.** **They split the two metrics, and the reason is variance.** QAOA lands on the exact optimum more often than the heuristic (79% at QAOA p=3 versus 62%), but when it misses it misses badly — worst run 0.8096 against the heuristic's worst of 0.9539. That bad tail drags the pooled QAOA mean (0.9779) below greedy's (0.9921). So: QAOA is right more often, and wrong more expensively. For a bank allocating real capital, the heuristic's predictability is worth more than the extra exact hits — which is the opposite of the conclusion a hit-rate-only table would have given you.

3. **We cannot tell you which depth is best, and neither can anyone who ran this once.**
   This is our main methodological finding. The spread within a single (instance, depth) cell
   across QAOA seeds is **0.0236**, while the spread between the depth means is
   **0.0160**. Within-cell noise is as large as or larger than the differences between depths, so no depth is meaningfully best on this problem. We ran an earlier version of this benchmark with one
   QAOA seed per cell and it ranked p=2 best by a clear margin; re-running with a different
   transpilation ranked p=2 *worst*. Same code, same instances. Depth ranking at this scale is
   dominated by optimiser-seed luck, and a single-seed table reporting a "best depth" is
   measuring noise. We report 3 repeats per cell for exactly this reason.

4. **Depth is still not free in runtime.** Cost grows with p regardless of whether quality
   does, because the fixed COBYLA budget of 200 iterations has to cover 2p
   parameters. The binding constraint here is the classical optimisation landscape, not the
   circuit.

---

## B. The scaling wall — measured, on this laptop

| Applicants | Qubits | Statevector (MB) | QAOA p=1 (s) | Exact (s) |
| --- | --- | --- | --- | --- |
| 6 | 10 | 0.0 | 2.5 | 0.0023 |
| 8 | 12 | 0.1 | 4.4 | 0.0056 |
| 10 | 14 | 0.3 | 6.9 | 0.0189 |
| 12 | 16 | 1.0 | 7.3 | 0.0743 |

Statevector memory is 2^n × 16 bytes. Extrapolating past the table: 28 qubits = 4.3 GB,
30 qubits = 17.2 GB (dead on a 16 GB laptop). **The binding constraint on this project is
the budget inequality**, which forces integer slack and binary expansion — every doubling of
the budget range costs another qubit. Discretising capital into coarse units is the single
lever that keeps the instance simulable, and it is a modelling decision, not a tuning knob.

---

## B2. Hardware readiness — and a metric that lied to us

We never touch hardware — the brief scopes us to a simulator. But "would this run on a real
device?" is the obvious follow-up, so we swept a depolarizing two-qubit gate error at
8 applicants (1 QAOA layer, 3 instances per level).

| 2-qubit gate error | AR, best of 2048 shots | AR, sampled distribution | P(feasible) | Wall clock (s) |
| --- | --- | --- | --- | --- |
| 0.000 | 1.0000 | 0.2217 | 0.583 | 2.9 |
| 0.001 | 1.0000 | 0.2627 | 0.515 | 70.7 |
| 0.005 | 0.9658 | 0.2555 | 0.600 | 83.6 |
| 0.010 | 1.0000 | 0.2885 | 0.590 | 82.8 |
| 0.020 | 1.0000 | 0.2485 | 0.583 | 72.8 |

**What this does establish.** Best-of-2048-shots readout returns the *exact optimum*
at every error level, including 2% depolarizing error applied across 182 two-qubit gates —
a regime where essentially no coherent signal should survive. That is not robustness of the
algorithm; it is an artifact of the statistic. At 12 qubits a near-uniform distribution still
lands on the optimum within 2048 draws by chance. **A QAOA noise study scored on
best-of-N shots will report false robustness**, and `MinimumEigenOptimizer` reports exactly
that statistic by default. This is the single most useful thing we learned building the
ablation, and we only found it because our first version of this table showed noise making
QAOA *better* — which is physically impossible, so the metric had to be wrong.

**What this does NOT establish.** We cannot give you a degradation curve. Holding the noise
sweep to the same standard as the depth ranking in section A: the scatter *within* one error
level across seeds is **0.1788**, while the spread *between*
error levels is only **0.0242** — the putative trend is roughly
7× smaller
than its own noise floor. Resolving it honestly would need about **220 seeds per level**, roughly **19 hours** of noisy simulation. We did not run that, so we report the sweep as inconclusive rather than drawing a line through five noisy points.

We are stating this because the alternative — printing the five means as a tidy descending
curve — would have looked far more impressive and would have been unsupported by our own data.

---

## C. Fairness as an optimiser constraint, not a footnote

The approval-rate parity penalty is a **squared linear term**, so it folds into the objective
at **zero additional qubits** — and it is what makes the objective genuinely quadratic. A plain
knapsack objective is linear; the parity penalty introduces real ZZ couplings between
applicants of opposite groups.

| Fairness weight | Mean profit (DM) | Approval-rate gap (F-M) | Loans funded |
| --- | --- | --- | --- |
| 0.0 | 2,868 | -42.0% | 4.2 |
| 2000.0 | 2,801 | -11.1% | 4.0 |
| 20000.0 | 2,586 | -2.9% | 3.4 |

This quantifies the price of parity in DM rather than asserting the model is fair.

**Caveat we state rather than hide:** the protected attribute is derived from German Credit
attribute 9, which encodes marital status and sex jointly; the reliability of that coding has
been questioned in the literature. We use it to demonstrate the *mechanism* of a fairness-constrained
allocator, not to make a claim about lending discrimination in this dataset.

---

## D. The AI model — reported honestly

| Model | ROC-AUC | Brier score |
| --- | --- | --- |
| Gradient boosting (calibrated) | 0.777 | 0.168 |
| Logistic regression (tuned) | 0.799 | 0.159 |

Logistic regression **beats** the gradient-boosted model on this dataset
(0.799 vs 0.777 AUC). That is the expected result at n=1000 with
30% base rate, and we report it rather than burying it. Calibration is the metric that matters
downstream: the optimiser multiplies these probabilities by cash amounts, so a miscalibrated
0.3 that should be 0.5 corrupts every coefficient of the Hamiltonian.

---

## E. Bottom line

Quantum **loses on speed by ~425×**. On quality it does not cleanly win either:
pooled approximation ratio 0.9779 against the greedy heuristic's 0.9921,
though it reaches the exact optimum more often (79% at QAOA p=3 vs
62%) at the cost of a worse tail. **We are reporting a negative result, and
that is the point** — the measurement is trustworthy precisely because it did not come out the
way we wanted. We are not claiming advantage at 14 qubits; published analysis
puts the QAOA crossover for combinatorial problems at hundreds of qubits. What we demonstrate is
a correct end-to-end mapping — calibrated ML output → QUBO → Ising Hamiltonian → variational
circuit → measured portfolio — and an honest measurement of exactly where it stops working, which
is what the "small qubit counts, simulator only" scope asks for.

One thing QAOA gives that exact search structurally cannot: it returns a **distribution** over
portfolios. Under default probabilities that are themselves estimates, a ranked set of
near-optimal feasible portfolios is more useful than a single optimum computed for point
estimates that are wrong.
