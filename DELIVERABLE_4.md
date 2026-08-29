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
| QAOA p=1 | 0.9771 | 0.9083 | 0.0317 | 50% | 5.2 |
| QAOA p=2 | 0.9830 | 0.9172 | 0.0289 | 67% | 7.1 |
| QAOA p=3 | 0.9764 | 0.9083 | 0.0319 | 50% | 10.1 |

Classical references on the same instances:

| Solver | Approx ratio (mean) | Hit exact optimum | Wall clock (s) |
| --- | --- | --- | --- |
| Exact (brute force) | 1.0000 | 100% | 0.0599 |
| Greedy (value/capital) | 0.9986 | 88% | 0.0002 |

### What this actually says

1. **QAOA is competitive on quality and hopeless on speed.** Pooled across all depths and
   repeats, QAOA averages **0.9789** and hits the exact optimum on
   **56%** of runs, taking **7.5 s** against **0.0599 s**
   for exhaustive classical search — roughly **125× slower**. At 14 qubits there
   is no honest speed claim to make, and any team reporting a quantum speed win at this scale
   benchmarked against a crippled baseline.

2. **QAOA versus the heuristic a bank would actually deploy.** **The heuristic wins.** Greedy averages 0.9986 against pooled QAOA's 0.9789, at 0.0002s versus 7.5s. On this problem, at this scale, the greedy heuristic is simply the better tool and QAOA has no metric to stand on beyond demonstrating the mapping.

3. **We cannot tell you which depth is best, and neither can anyone who ran this once.**
   This is our main methodological finding. The spread within a single (instance, depth) cell
   across QAOA seeds is **0.0211**, while the spread between the depth means is
   **0.0036**. Within-cell noise is as large as or larger than the differences between depths, so no depth is meaningfully best on this problem. We ran an earlier version of this benchmark with one
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
| 6 | 10 | 0.0 | 1.9 | 0.0036 |
| 8 | 12 | 0.1 | 3.7 | 0.0135 |
| 10 | 14 | 0.3 | 4.6 | 0.0590 |
| 12 | 16 | 1.0 | 7.2 | 0.2516 |

Statevector memory is 2^n × 16 bytes. Extrapolating past the table: 28 qubits = 4.3 GB,
30 qubits = 17.2 GB (dead on a 16 GB laptop). **The binding constraint on this project is
the budget inequality**, which forces integer slack and binary expansion — every doubling of
the budget range costs another qubit. Discretising capital into coarse units is the single
lever that keeps the instance simulable, and it is a modelling decision, not a tuning knob.

---

## B2. Hardware readiness — and a metric that lied to us

We never touch hardware — the brief scopes us to a simulator. But "would this run on a real
device?" is the obvious follow-up, so we swept a depolarizing two-qubit gate error at
8 accounts (1 QAOA layer, 12 instances per level).

| 2-qubit gate error | AR, best of 2048 shots | AR, sampled distribution | P(feasible) | Wall clock (s) |
| --- | --- | --- | --- | --- |
| 0.000 | 0.9351 | 0.3172 | 0.616 | 3.1 |
| 0.001 | 1.0000 | 0.3200 | 0.629 | 65.4 |
| 0.005 | 0.9601 | 0.3683 | 0.605 | 68.7 |
| 0.010 | 0.9762 | 0.3656 | 0.591 | 64.8 |
| 0.020 | 0.9188 | 0.3683 | 0.547 | 62.9 |

**This sweep is inconclusive, and the interesting part is why.** Scatter *within* a single
error level across seeds is **0.1365**; the spread *between*
error levels is **0.0268**. The putative trend is about
5x smaller than its own noise floor, so there is no degradation curve here we are
entitled to draw. Resolving it would take roughly **104
seeds per level**, about **8 hours** of noisy simulation.

**The power calculation was itself under-powered.** We first ran this at 3 seeds per level.
That pilot was also inconclusive, but it estimated only ~8 seeds would settle it — so we ran
12. With 12 seeds the measured within-level scatter came out roughly 2.5x larger than the
pilot had estimated, and the requirement moved from ~8 seeds to ~104.
The pilot had not merely failed to resolve the trend; it had *underestimated its own error
bars*. This is the same lesson as section A applied one level up: a small sample is unreliable
about effects, and equally unreliable about how much data you would need to measure them.

**A claim we are retracting.** On the 3-seed data, best-of-2048-shots readout returned
the exact optimum at every error level including 2%, and we wrote that up as evidence that the
default statistic is blind to noise — a good story, and `MinimumEigenOptimizer` does report
that statistic by default. At 12 seeds it does not hold: best-of-N ranges from
0.9188 to 1.0000 across the sweep. Both metrics move, and both move by less than
the within-level scatter, so neither supports a conclusion. We are removing the claim rather
than keeping it because it read well.

We report all of this because the alternative — five means printed as a tidy descending
curve — would have looked far more impressive and would have been unsupported by our own data.

---

## B3. The two numbers we invented, and why only one of them matters

The dataset contains no interest rate and no recovery rate, so the loan economics —
**18% APR** and **60% loss-given-default** — are assumptions we
chose, not measurements. Every expected-value coefficient, and therefore the QUBO's ground
state, rests on them. That is a fair thing for a judge to attack, so we tested it.

**First result: there is only one free parameter, not two.** Expanding the expected value,

    EV_i = A_i · [ (1 − p_i)·APR − p_i·LGD ]
         = A_i · APR · [ (1 − p_i) − p_i·(LGD/APR) ]

scaling APR and LGD together by any k > 0 scales every EV by k, and a knapsack's argmax is
invariant under positive scaling. So the portfolio depends only on **ρ = LGD/APR**. Our
baseline is simply one point on the line ρ = 3.33. We confirmed this
empirically rather than trusting the algebra: identical portfolios across all 24 rescaling checks.

**Second result: the allocation is robust; the screening is not.**

| rho = LGD/APR | LGD at base APR | Same-pool overlap | Full-pipeline overlap | Accounts funded |
| --- | --- | --- | --- | --- |
| 1.50 | 0.27 | 0.581 | 0.000 | 2.9 |
| 2.00 | 0.36 | 0.775 | 0.000 | 3.1 |
| 2.50 | 0.45 | 0.850 | 0.000 | 3.1 |
| 3.33 | 0.60 | 1.000 | 1.000 | 3.1 |
| 4.00 | 0.72 | 1.000 | 0.000 | 3.2 |
| 5.00 | 0.90 | 0.950 | 0.000 | 3.8 |
| 7.00 | 1.26 | 0.750 | 0.000 | 3.9 |

Holding the candidate pool fixed, a modest error in ρ leaves **98%**
of the portfolio unchanged, and across the full swept range of ρ the overlap averages
**82%**. But run the *full* pipeline — where a different ρ also
changes which applicants clear the positive-EV screen — and overlap collapses to
**0%**.

That contrast is the useful finding. ρ barely affects *which of the fundable loans to pick*; it
almost entirely determines *who is fundable at all*. The quantum optimiser's output is stable
against our pricing assumptions. The screening step in front of it is not, and a real lender
would need to estimate ρ carefully — that is a credit-policy question, not an optimisation one.

We separated these two effects only after noticing that our first version of this measurement
conflated them and reported a misleading 0% everywhere.

---

## B4. What we took from comparable work, and what we measured

We surveyed comparable public work before finalising: the Qiskit Finance
`PortfolioOptimization` tutorial, IBM's Quantum Challenge portfolio notebooks, and the
strongest QAOA portfolio repositories on GitHub. Two ideas were worth borrowing.

**Adopted: a genuine risk term.** Our objective was expected value under a budget — a knapsack,
not a portfolio. The canonical mean-variance formulation pairs a linear return term with a
quadratic risk term, so we added one: a Herfindahl penalty on capital concentrated in a single
loan purpose, using the `purpose` column we had been ignoring. Sector concentration limits are
how credit books are actually managed, loans in one sector default together, and the penalty
introduces real ZZ couplings between same-sector applicants at **zero extra qubits**. This is
the change that makes the problem a portfolio problem rather than item selection.

**Tested and not adopted: CVaR aggregation.** Barkoutsos et al. (*Quantum* **4**, 256 (2020))
report that aggregating QAOA samples by the Conditional Value-at-Risk of the best α-fraction,
instead of by their mean, converges faster and better on every combinatorial problem they
tested — and it is what the strongest comparable repositories use. It is a one-parameter change
in Qiskit. We measured it over 64 runs per setting:

| Aggregation | AR mean | AR worst | Std | Hit optimum | Sec |
| --- | --- | --- | --- | --- | --- |
| CVaR alpha=0.1 | 0.9894 | 0.8522 | 0.0260 | 78% | 4.5 |
| CVaR alpha=0.25 | 0.9831 | 0.9140 | 0.0274 | 70% | 4.4 |
| CVaR alpha=0.5 | 0.9788 | 0.9001 | 0.0327 | 58% | 4.3 |
| mean (default) | 0.9756 | 0.8132 | 0.0384 | 58% | 4.4 |

The best setting, CVaR alpha=0.1, scores 0.9894 against the default's
0.9756 — an improvement of **+0.0138**. But the scatter within
a single (instance, setting) cell is **0.0258**, against a spread between
settings of only **0.0060**. The effect is roughly 4× smaller than the noise floor, so we kept the default and say so here.

That is not a contradiction of the paper. CVaR's reported advantage is largest on noisy hardware
and on problems where the mean-aggregated landscape is hard to optimise; at 14 qubits on a noise-
free simulator the default already reaches the optimum 58% of the time, leaving
almost nothing for a better aggregation to recover. **We report this because adopting a technique
on the strength of its citation, without checking it helps on your own problem, is how unverified
claims get into submissions.**

---

## C. Fairness and diversification as optimiser constraints, not footnotes

Both penalties are **squared linear terms**, so each folds into the objective at **zero
additional qubits** — and together they are what make the objective genuinely quadratic. A plain
knapsack objective is linear. Sector concentration couples applicants in the *same* sector;
approval-rate parity couples applicants in *opposite* groups.

| Fairness weight | Mean profit (DM) | Approval-rate gap (F-M) | Accounts funded |
| --- | --- | --- | --- |
| 0.0 | 33,195 | -20.6% | 2.8 |
| 2000.0 | 33,195 | -20.6% | 2.8 |
| 20000.0 | 32,685 | -7.6% | 2.6 |

This quantifies the price of parity in DM rather than asserting the model is fair.

**Why sex is usable here, and was not before.** We built this on UCI Statlog (German Credit)
first. Grömping (2019), *South German Credit Data: Correcting a Widely Used Data Set*
(Report 4/2019, Beuth University of Applied Sciences Berlin), shows that dataset's published
coding is wrong: male singles and female non-singles share code `A92`, and in the published
file `A95` (female:single) has **zero rows** — so any "female" group is a mixed bag and a
fairness number computed on it measures nothing. Most published fairness work on German Credit
uses exactly that variable. This dataset codes sex unambiguously, which is one of the reasons
we moved to it. `SEX` and the group label derived from it are excluded from the classifier's
features, so the model cannot condition on sex directly.

**And the base rate is real.** German Credit's 30% default rate is an artefact of a stratified
sample with bad credits heavily oversampled (700 good / 300 bad by construction), which inflated
every expected-value figure. Here the 22.1% rate is the observed rate in 30,000 accounts, so the
money on this page is in realistic proportions.