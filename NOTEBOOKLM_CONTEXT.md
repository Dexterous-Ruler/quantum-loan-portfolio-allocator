# Quantum-Assisted Loan-Portfolio Allocator — Complete Project Context

> **Purpose of this document:** a single self-contained briefing on the project, written to be
> uploaded as a source so a presentation can be generated from it. Every number below is a
> measured result produced by scripts in the repository, not an estimate.

---

## 1. Identity

| Field | Value |
| --- | --- |
| **Project title** | Quantum-Assisted Loan-Portfolio Allocator |
| **Team** | ASTITWA |
| **Member** | Tanishq Aryan |
| **Event** | IEEE Quantum AI Hackathon 2026 |
| **Theme** | #25 — Portfolio / Resource Allocation Optimizer |
| **Domain** | Optimization / Finance |
| **Deadline** | 29 August 2026, 5:00 pm |
| **GitHub repository** | https://github.com/Dexterous-Ruler/quantum-loan-portfolio-allocator (public) |
| **Dataset** | https://archive.ics.uci.edu/dataset/350/default+of+credit+card+clients |

Repository contains 53 tracked files across 11 commits.

---

## 2. The one-sentence pitch

A bank has more creditworthy customers than it has capital. A classical AI model prices the
risk of each customer; a quantum optimiser chooses which subset to actually fund.

---

## 3. Problem statement

Classical credit scoring answers *"how risky is this customer?"* It does not answer *"which
combination of customers should we fund?"* — and the second question is the real business
decision.

Choosing the subset of accounts that maximises risk-adjusted return, subject to a fixed capital
budget, while controlling concentration risk and approval-rate disparity, is a **0-1 knapsack
with quadratic penalty terms**. That problem is:

- **NP-hard** (weakly, for the knapsack; the constrained variants harder)
- **Natively binary** — every decision is fund / don't fund
- **Natively quadratic** — once risk and fairness terms are included

Those three properties are precisely the structure quantum optimisation algorithms are built
for, which is why quantum is a defensible choice here rather than decoration.

---

## 4. The architectural idea — "in series, not in parallel"

**This is the single most important point in the whole project.**

Most hybrid quantum-AI hackathon projects run their two halves **in parallel**: train a
classical classifier, then train a quantum classifier on the same task, and compare accuracy.
That is two demos bolted together — the quantum part could be deleted and the project would
still function.

This project runs them **in series**:

```
30,000 real credit-card accounts (UCI, Taiwan 2005)
      ↓
Calibrated gradient-boosted classifier  →  P(default) per customer
      ↓
EV = P(repay) × interest − P(default) × LGD × exposure
      ↓
QUBO:  maximise  Σ EV·x  −  γ·concentration(x)  −  λ·parity_gap(x)²
       subject to  Σ units·x  ≤  capital budget
      ↓
Ising Hamiltonian  →  QAOA ansatz  →  measured bitstring
      ↓
The winning bitstring IS the list of customers to fund
```

**The classifier's output literally parameterises the cost Hamiltonian.** Delete the AI model
and there is no optimisation problem left to solve. That dependency is the point.

---

## 5. The dataset — and why we changed it

**Current dataset:** UCI *Default of Credit Card Clients* (Taiwan, 2005) — 30,000 real accounts,
23 predictors, **real 22.1% default rate**, 21,000 train / 9,000 held-out test.

**We started on UCI Statlog (German Credit) — the standard credit-scoring benchmark — and
deliberately moved off it.** The comparison:

| | German Credit | Current dataset |
| --- | --- | --- |
| Rows | 1,000 | **30,000** |
| Vintage | 1973–75 | **2005** |
| Default rate | 30% — a *stratified over-sample*, 700/300 good/bad **by construction** | **22.1%, real** |
| Protected attribute | Sex **not recoverable** | Sex coded unambiguously |

**The deciding factor was a data-integrity problem.** Grömping (2019), *South German Credit
Data: Correcting a Widely Used Data Set* (Report 4/2019, Beuth University of Applied Sciences
Berlin), shows German Credit's published coding is wrong in places. Specifically, male singles
and female non-singles share code `A92`, and in the published file `A95` (female:single) has
**zero rows**. So every "female" label would come from the one code known to be mixed — meaning
a fairness result computed on it measures nothing. Most published fairness research on that
dataset uses exactly this variable.

The over-sampled base rate mattered too: it inflated every expected-value figure, so the money
was never realistic.

**Modelling choice this dataset forces:** it is revolving credit, so exposure at default is the
**outstanding balance**, not the credit limit. We use the latest statement balance clipped to
`[0, limit]`. Using the limit would overstate every position by roughly an order of magnitude.

**Remaining honest limitations:** one bank, one country, one six-month window in 2005; and the
segment used for concentration risk (education band) is a proxy for a real industry sector.

---

## 6. Deliverable 1 — The AI model

**Model:** scikit-learn `HistGradientBoostingClassifier` wrapped in `CalibratedClassifierCV`
(sigmoid / Platt scaling, 5-fold stratified).

| Model | ROC-AUC | Brier score |
| --- | --- | --- |
| **Gradient boosting (calibrated)** | **0.780** | **0.135** |
| Logistic regression (tuned) | 0.715 | 0.146 |

Gradient boosting wins on both metrics. Note this is the **reverse** of what we measured on the
1,000-row German Credit data, where tuned logistic regression won — boosting needs data to beat
a well-specified linear model, and 21,000 rows is enough.

**Why calibration is prioritised over raw accuracy:** the optimiser multiplies these
probabilities by cash amounts. A miscalibrated 0.3 that should be 0.5 corrupts every coefficient
of the downstream Hamiltonian. **Brier score is the headline metric, not AUC.**

**Fairness handling:** `SEX` and the group label derived from it are excluded from the feature
set, so the classifier cannot condition on sex directly. This does not make the model fair —
proxies remain — it means unfairness must be measured on *outcomes*, which is what the
optimiser's fairness term does.

Of 9,000 held-out accounts, **6,104 have positive expected value** and form the candidate pool.

---

## 7. Deliverable 2 — The quantum module

**One** quantum component, deliberately. The brief asks for "a single, well-scoped quantum
component," and the *Feasibility* criterion rewards being well-scoped — a second component would
cost points, not earn them.

**Algorithm:** QAOA (Quantum Approximate Optimization Algorithm) via `qiskit-optimization` 0.7.0
— cost layer `exp(−iγH_C)`, mixer layer `exp(−iβH_B)`, COBYLA as classical outer optimiser,
2,048 measurement shots per evaluation.

**Measured circuit facts (default 10-customer instance):**

| Property | Value |
| --- | --- |
| Qubits | **14** |
| Decision variables | 10 (fund / don't fund) |
| Slack qubits | 4 (binary expansion of the budget inequality) |
| Pauli terms in cost Hamiltonian | **105** |
| Variational parameters (p=1) | 2 |
| Transpiled circuit depth | **78** |
| Two-qubit gates | **182** |

**Hardware:** Qiskit Aer simulator only — the brief specifies small qubit counts, simulator
only, and we stayed inside that boundary deliberately.

**Qubit count formula:** `n + ceil(log2(budget + 1))`. The budget is an **inequality**, so
`QuadraticProgramToQubo` introduces an integer slack variable and binary-expands it. Discretising
capital into coarse units is the single lever controlling qubit count — and it is a modelling
decision, not a tuning knob.

**Both penalty terms cost ZERO additional qubits.** Concentration and parity are each *squared
linear forms*, so they fold into the objective without new variables, while introducing genuine
ZZ couplings:
- **Concentration** couples accounts in the **same** segment
- **Parity** couples accounts in **opposite** demographic groups

Without them the objective would be linear — a knapsack in a QUBO costume. With them, the
problem is quadratic by construction.

---

## 8. Deliverable 3 — The live demo

A Streamlit application. The jury interacts with three levers, and each one changes the
*problem*, causing a full re-solve:

1. **Capital budget slider** — the funded portfolio re-optimises; a marker tracks position on a
   profit-vs-budget curve showing diminishing returns
2. **"Diversify across segments" toggle** — concentration drops, and the app reports what
   diversification *cost* in money
3. **Fairness toggle** — the approval-rate gap closes, and the app reports the profit price

The demo also exposes the actual circuit (qubits, depth, two-qubit gate count), the largest
Pauli terms of the cost Hamiltonian, and the ranked distribution of alternative portfolios.

The default configuration is **pre-warmed at startup**, so the first optimisation returns
instantly rather than pausing for several seconds.

---

## 9. Deliverable 4 — Quantum vs classical, measured honestly

**Setup:** all solvers attack the **identical QUBO on the identical instances**. This compares
*optimisers*, not two different classifiers. 8 instances × 3 optimiser seeds = 24 runs per depth,
2,048 shots, COBYLA maxiter 200, 14 qubits.

### Headline results

| Solver | Approx. ratio (mean) | Worst | Std | Hit exact optimum | Wall clock |
| --- | --- | --- | --- | --- | --- |
| Exact (brute force) | 1.0000 | 1.0000 | 0.0000 | 100% | 0.060 s |
| **Greedy heuristic** | **0.9986** | 0.9889 | 0.0039 | **87.5%** | **0.0002 s** |
| QAOA p=1 | 0.9771 | 0.9083 | 0.0317 | 50.0% | 5.19 s |
| QAOA p=2 | 0.9830 | 0.9172 | 0.0289 | 66.7% | 7.13 s |
| QAOA p=3 | 0.9764 | 0.9083 | 0.0319 | 50.0% | 10.10 s |

**Pooled QAOA: approximation ratio 0.9789, hits the exact optimum on 55.6% of runs, 7.47 s per
solve — roughly 125× slower than exhaustive search.**

### The honest bottom line

**Quantum loses.** It is ~125× slower than exhaustive search AND it loses to the greedy
heuristic on both quality metrics. We report this as the headline rather than hiding it.

We do not claim quantum advantage at 14 qubits. Guerreschi & Matsuura, *"QAOA for Max-Cut
requires hundreds of qubits for quantum speed-up"*, **Scientific Reports 9:6903 (2019)**,
doi:10.1038/s41598-019-43176-9, place the crossover for combinatorial problems at hundreds of
qubits. What this project demonstrates is a **correct end-to-end mapping** and an **honest
measurement of exactly where it breaks** — which is what the brief's "small qubit counts,
simulator only" scope asks for.

### The scaling wall (measured)

| Customers | Qubits | Statevector memory | QAOA p=1 | Exact |
| --- | --- | --- | --- | --- |
| 6 | 10 | 0.02 MB | 1.87 s | 0.004 s |
| 8 | 12 | 0.07 MB | 3.72 s | 0.014 s |
| 10 | 14 | 0.26 MB | 4.62 s | 0.059 s |
| 12 | 16 | 1.05 MB | 7.16 s | 0.252 s |

Statevector memory is 2ⁿ × 16 bytes. Extrapolating: 28 qubits = 4.3 GB, 30 qubits = 17.2 GB —
dead on a 16 GB laptop.

---

## 10. The four findings that came from auditing our own work

**This is the strongest part of the submission.** Each finding came from checking a result that
already looked finished. Three of them are retractions.

### Finding 1 — The QAOA depth ranking does not survive its own noise floor

- Scatter **within** a single (instance, depth) cell across optimiser seeds: **0.0211**
- Spread **between** depth means: **0.0036**

The apparent ranking is roughly **6× smaller than its own noise**. An early single-seed version
of this benchmark ranked p=2 clearly *best*; re-running with different transpilation ranked p=2
clearly *worst* — same code, same instances. **Anyone reporting a "best depth" from one seed is
reporting noise.** We now run 3 seeds per cell for exactly this reason.

### Finding 2 — A metric that lied, caught because it was physically impossible

Our first noise ablation showed noise making QAOA **better**. That is physically impossible, so
the metric had to be wrong. Cause: `MinimumEigenOptimizer` returns the **best bitstring out of
2,048 shots**, and at 12 qubits even a heavily depolarized, near-uniform distribution still
samples the optimum by chance. We added a distribution-level metric (expected objective over the
sampled distribution) that can actually respond to noise.

### Finding 3 — The power calculation was itself under-powered *(retraction)*

The noise sweep is **inconclusive**, and the reason is instructive:

- Scatter within one error level: **0.1365**
- Spread between error levels: **0.0268**

The trend is ~5× smaller than its own noise floor. Resolving it honestly would need **~104 seeds
per level, about 7.7 hours** of noisy simulation.

But here is the lesson: our 3-seed pilot was also inconclusive and estimated only **~8 seeds**
would settle it. At 12 seeds, the measured scatter came out **~2.5× larger** than the pilot had
estimated, pushing the requirement to ~104. **The pilot had not merely failed to resolve the
trend — it had underestimated its own error bars.** A small sample is unreliable about effects,
and equally unreliable about how much data you would need to measure them.

**We also retracted a claim.** On 3-seed data, best-of-2,048-shots readout returned the exact
optimum at *every* error level including 2% gate error, and we wrote that up as clean evidence
that Qiskit's default statistic is blind to noise. At 12 seeds it ranges 0.9188 to 1.0000 and
the claim does not hold. We removed it — it read well, but it was not supported.

### Finding 4 — Only one of our two invented numbers matters

The dataset has no interest rate and no recovery rate, so **18% APR** and **60% loss-given-default**
are assumptions we chose. Expanding the expected value:

```
EV_i = A_i · [ (1 − p_i)·APR − p_i·LGD ]
     = A_i · APR · [ (1 − p_i) − p_i·(LGD/APR) ]
```

Scaling APR and LGD together by any k > 0 scales every EV by k — and a knapsack's argmax is
**invariant under positive scaling**. So the portfolio depends only on **ρ = LGD/APR**, not on
either number individually. Confirmed empirically across 24 rescaling checks, and pinned by a
unit test.

Sensitivity to ρ, holding the candidate pool fixed:
- Near the baseline: **97.5% portfolio overlap**
- Across the full swept range: **81.8% overlap**
- But through the **full pipeline** (where ρ also changes who clears the positive-EV screen):
  **0% overlap**

**The allocation is robust to our pricing assumptions; the screening step in front of it is
not.** ρ barely affects which of the fundable accounts to pick — it almost entirely determines
who is fundable at all. That is a credit-policy question, not an optimisation one.

*(We separated these two effects only after noticing our first version of this measurement
conflated them.)*

---

## 11. Competitive scan — what we borrowed and what we rejected

We surveyed the Qiskit Finance `PortfolioOptimization` tutorial, IBM's Quantum Challenge
portfolio notebooks, and comparable QAOA portfolio repositories before finalising.

**ADOPTED — a genuine risk term.** Our objective was expected value under a budget: that is a
knapsack, not a portfolio. The canonical mean-variance formulation pairs a linear return term
with a quadratic risk term, so we added a **Herfindahl concentration penalty** on capital piled
into one customer segment. Segment concentration limits are how credit books are actually
managed, because accounts in a segment default together. Costs zero extra qubits. Verified
against brute force across 18 combinations of γ, λ and seed.

**TESTED AND REJECTED — CVaR aggregation.** Barkoutsos et al., *Quantum* **4**, 256 (2020),
report CVaR aggregation converging faster and better on every combinatorial problem they tested,
and it is what the strongest comparable repositories use. It is a one-parameter change. We
measured it over 64 runs per setting:

- Best setting (CVaR α=0.1): **0.9894** vs default **0.9756** — improvement **+0.0138**
- Within-cell scatter: **0.0258** — roughly **4× larger** than the between-setting spread

**Inconclusive.** We kept the default and documented why. This is not a contradiction of the
paper: CVaR's advantage is largest on noisy hardware and hard optimisation landscapes, and at 14
noiseless qubits the default already reaches the optimum most of the time. *Adopting a technique
on the strength of its citation, without checking it helps on your own problem, is how
unverified claims get into submissions.*

**DELIBERATELY SKIPPED — warm-start QAOA / XY mixers.** XY mixers preserve Hamming weight, so
they suit *cardinality* constraints. Ours is a budget **inequality** with heterogeneous weights,
so they do not apply without reformulating. High effort, unclear payoff, and it would break the
well-scoped story that *Feasibility* rewards.

---

## 12. Fairness and diversification, quantified

The project does not claim the model is fair. It claims it can **price** fairness.

| Fairness weight λ | Mean profit | Approval-rate gap | Accounts funded |
| --- | --- | --- | --- |
| 0 | 33,195 | −0.206 | 2.8 |
| 2,000 | 33,195 | −0.206 | 2.8 |
| 20,000 | 32,685 | −0.076 | 2.6 |

At demo-scale settings the approval-rate gap closes from roughly **0.28 to 0.03 for about 4% of
profit**. Diversification behaves the same way: concentration falls measurably and the app
reports the exact cost in money.

**Caveat stated openly:** this demonstrates the *mechanism* of a parity-constrained allocator.
It is not a finding about lending discrimination in Taiwan in 2005.

---

## 13. Technology stack

```
Python 3.14        qiskit==2.5.2        qiskit-aer==0.17.2
qiskit-optimization==0.7.0              scikit-learn        pandas / numpy / scipy
streamlit          matplotlib           pytest              xlrd
```

Pinned deliberately: `qiskit-optimization` requires `qiskit<3`, and QAOA/COBYLA moved **into**
`qiskit_optimization` at 0.7.0 — so tutorials importing them from `qiskit_algorithms` fail.

**Engineering practices:** 22 automated tests, GitHub Actions CI, and every number in both
Deliverable-4 documents is **generated from measured CSVs** — none is typed by hand, so a page
cannot silently drift from the experiment it reports.

The load-bearing test is `test_bruteforce_matches_qubo_diagonalisation`: if the converter's
penalty weights were wrong, exhaustive enumeration and exact diagonalisation of the QUBO would
disagree and every downstream number would be meaningless. **That test caught a real bug** — a
group label was updated in one place and missed in the QUBO builder, causing the Hamiltonian to
treat all applicants as one group and silently turning the fairness term into a constant.
Nothing raised an error; only the test caught it.

---

## 14. Repository contents

| Path | What it is |
| --- | --- |
| `src/data.py` | Dataset download, loan economics, protected attribute |
| `src/ai_model.py` | **Deliverable 1** — calibrated classifier + baseline |
| `src/portfolio.py` | QUBO construction, concentration and parity terms |
| `src/solvers.py` | **Deliverable 2** — QAOA, plus exact and greedy classical solvers |
| `app.py` | **Deliverable 3** — Streamlit live demo |
| `DELIVERABLE_4.html` | **Deliverable 4** — the literal one-page A4 comparison |
| `DELIVERABLE_4.md` | Long-form version with all ablations |
| `PRESENTATION.pptx` | 8-slide deck |
| `PITCH.md` | 3-minute demo script + judge Q&A |
| `src/benchmark.py` | QAOA vs classical benchmark |
| `src/noise_ablation.py` | Depolarizing-noise sweep, hardware readiness |
| `src/sensitivity.py` | Sensitivity to the assumed loan economics |
| `src/cvar_ablation.py` | CVaR aggregation — tested, not adopted |
| `tests/test_core.py` | 22 correctness tests |
| `run_all.py` | Rebuilds every deliverable end to end |

---

## 15. How it maps to the judging criteria

**Innovation** — Fairness and diversification enter as *squared penalties inside the objective*,
costing zero extra qubits while creating the ZZ couplings that make the Hamiltonian genuinely
quadratic. The AI feeds the quantum module in series rather than duplicating it.

**Technical quality** — Every claim is measured, reported with spread rather than single runs,
and tested against its own noise floor. Three claims were retracted when more data did not
support them. All documents are generated from data.

**Feasibility** — 10–16 qubits, simulator only, no hardware queue. A fresh clone regenerates
byte-identical output. Deliberately one quantum module.

**Completeness** — All four deliverables present and working, plus deck, pitch script, tests,
CI, four ablations and a demo animation.

---

## 16. Suggested presentation narrative

A deck built from this material should follow this arc:

1. **The problem** — more creditworthy customers than capital; which subset to fund is NP-hard
2. **Why quantum belongs here** — 0-1 knapsack, natively binary and quadratic, not curve-fitting
3. **The architecture** — AI feeds quantum *in series*; say the word "series"
4. **The live demo** — budget, diversification and fairness sliders; each one is *priced*
5. **The honest comparison** — lead with the loss: classical wins at this scale
6. **What we learned by auditing ourselves** — the depth ranking, the lying metric, the
   under-powered power calculation
7. **The scaling wall** — where this stops being simulable, and why we scoped it here
8. **Bottom line** — a correct end-to-end mapping and an honest map of its limits

### Three things to say out loud

- *"The AI and quantum modules run in **series**. Remove the model and there is no quantum
  problem left."*
- *"We are reporting a **negative result**, and that is the point — it is trustworthy precisely
  because it did not come out the way we wanted."*
- *"Our own first benchmark was wrong, and we caught it. Three times."*

### Three things never to say

- **Never claim a quantum speedup** — the numbers are on our own comparison page
- **Never say the model is "fair"** — say we can *price* parity
- **Never quote absolute profit as a real P&L** — it is one 10-account slice of a 2005 card book

---

## 17. Key citations

- **Guerreschi, G. G. & Matsuura, A. Y.** "QAOA for Max-Cut requires hundreds of qubits for
  quantum speed-up." *Scientific Reports* **9**, 6903 (2019). doi:10.1038/s41598-019-43176-9
- **Barkoutsos, P. K. et al.** "Improving Variational Quantum Optimization using CVaR."
  *Quantum* **4**, 256 (2020).
- **Grömping, U.** "South German Credit Data: Correcting a Widely Used Data Set." Report 4/2019,
  Beuth University of Applied Sciences Berlin.
- **Dataset:** UCI Machine Learning Repository, *Default of Credit Card Clients*, dataset 350.
