# Quantum-Assisted Loan-Portfolio Allocator

**Hackathon theme #25 — Portfolio / resource allocation optimizer.**
*AI predicts returns from history → QAOA picks the best subset under a budget constraint →
live demo: enter a budget, get the optimized selection.*

An ML model scores loan applications for default risk; those calibrated probabilities become
the coefficients of a QUBO; QAOA allocates a fixed capital budget across the loan book.

## The architecture point

In most hybrid hackathon projects the AI and quantum parts run **in parallel** — train a
classifier, then train a quantum classifier on the same task and compare. Two demos bolted
together.

Here they run **in series**:

```
German Credit data
      ↓
calibrated GBM  →  P(default) per applicant
      ↓
EV = P(repay)·interest − P(default)·LGD·principal      ← ML output becomes objective coefficients
      ↓
QUBO: max Σ EV·x − λ·parity_gap(x)²   s.t.  Σ units·x ≤ budget
      ↓
Ising Hamiltonian  →  QAOA ansatz  →  measured portfolio
```

The classifier's output literally parameterises the cost Hamiltonian. Remove the AI and there
is no optimisation problem to solve.

## The four deliverables

| # | Deliverable | Where |
| --- | --- | --- |
| 1 | Working AI model | [`src/ai_model.py`](src/ai_model.py) — calibrated GBM + tuned logistic-regression baseline |
| 2 | One small quantum module | [`src/solvers.py`](src/solvers.py) — QAOA on the portfolio QUBO, 10–16 qubits, simulator |
| 3 | Live demo | [`app.py`](app.py) — Streamlit; budget slider re-optimises the loan book live |
| 4 | 1-page comparison | [`DELIVERABLE_4.html`](DELIVERABLE_4.html) — the literal one-pager, print to PDF. [`DELIVERABLE_4.md`](DELIVERABLE_4.md) is the long-form version |

Both Deliverable-4 documents are **generated from the measured CSVs** — no number in either
is typed by hand, so the page cannot drift from the experiment.

Supporting material: [`PRESENTATION.pptx`](PRESENTATION.pptx) (7-slide deck, also generated
from the artifacts) and [`PITCH.md`](PITCH.md) (3-minute demo script plus the questions a
quantum-literate judge will ask, with answers).

```bash
node src/make_deck.js && python src/qa_deck.py
```

`qa_deck.py` checks the deck for off-slide shapes, tight margins, overlapping text boxes and
text that will not fit its container — this machine has no LibreOffice, so the deck cannot be
rendered to images for visual inspection and the geometry is checked numerically instead.

Deliverable 2 is deliberately **one** module. The brief says "a single, well-scoped quantum
component", and *Feasibility* rewards being well-scoped — a second quantum component would cost
points, not earn them.

## Setup

```bash
py -3.14 -m venv .venv
```

```bash
.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Rebuild every deliverable end to end (~12 min, dominated by the benchmark):

```bash
.venv/Scripts/python.exe run_all.py
```

Regenerate only figures and pages from existing results (~20 s):

```bash
.venv/Scripts/python.exe run_all.py --fast
```

Launch the demo:

```bash
.venv/Scripts/streamlit run app.py
```

## Tests

```bash
.venv/Scripts/python.exe -m pytest tests -q
```

19 tests. The fast 16 run in ~7 s; three more exercise the QAOA solver and are marked `slow`
(`pytest tests -m slow`). The load-bearing one is
`test_bruteforce_matches_qubo_diagonalisation` — if the converter's penalty weights were
wrong, exhaustive enumeration and exact diagonalisation of the QUBO would disagree and every
downstream number in this repo would be meaningless.

CI additionally asserts that regenerating the Deliverable-4 documents is a **no-op**: if a
page has drifted from the experiment it reports, the build fails.

## Hardware readiness

The brief scopes us to a simulator, but "would this run on a real device?" has a measurable
answer. `src/noise_ablation.py` sweeps a depolarizing two-qubit gate error and reports the
error rate at which QAOA's approximation ratio falls below the classical heuristic — i.e. the
gate fidelity this circuit would need to be worth running. Noisy simulation is ~24× slower
than noiseless, so the sweep uses 12 qubits and p=1.

## Design decisions worth defending to a judge

**Why quantum here at all?** Subset selection under a budget is a 0-1 knapsack — weakly
NP-hard, natively binary, natively quadratic once the fairness term is included. It maps to an
Ising Hamiltonian whose ground state *is* the answer. This is categorically different from
running a quantum kernel on four PCA components, where the kernel is a similarity function
nobody can motivate. Expect the question and answer it before it is asked.

**Why the budget is the qubit bottleneck.** The capital constraint is an *inequality*, so
`QuadraticProgramToQubo` introduces an integer slack variable and binary-expands it, costing
`ceil(log2(budget+1))` extra qubits. Discretising capital into coarse units is what keeps the
instance simulable. Pool sizes map to qubits as: 6→10, 8→12, 10→14, 12→16.

**Why fairness is a penalty, not a constraint.** A second inequality constraint would add more
slack qubits. A squared parity gap folds into the objective at **zero** qubit cost — and it is
what makes the objective genuinely quadratic, producing real ZZ couplings between applicants of
opposite groups. A plain knapsack objective would be linear.

**Why shot-based sampling, not exact statevector expectation.** Measurement sampling is part of
the quantum concept being demonstrated, and it produces the ranked distribution of near-optimal
portfolios — something a single MILP optimum structurally cannot provide.

**Why we report 3 QAOA seeds per cell, not 1.** QAOA is stochastic in two independent ways:
which instance you drew, and which seed the sampler and optimiser started from. Running one
seed per cell confounds them. We learned this the hard way — an early single-seed benchmark
ranked `p=2` clearly best; re-running the same code with different transpilation ranked `p=2`
clearly *worst*. The spread within a single (instance, depth) cell is as large as the spread
between depths, so **no depth is meaningfully best at this scale** and any table claiming one
is reporting noise.

## Honest limitations

- **QAOA is ~1000× slower than exhaustive classical search at this size.** We do not claim a
  speed advantage; we measure the gap and show where the method stops being simulable.
- Beyond ~20 qubits the statevector simulation falls off a cliff (28 qubits = 4.3 GB).
- The protected attribute derives from German Credit attribute 9, which encodes marital status
  and sex jointly; that coding's reliability has been questioned. It demonstrates the mechanism
  of a fairness-constrained allocator, not a finding about lending discrimination.
- Logistic regression outperforms the gradient-boosted model on this dataset. We report it.

## Stack

Pinned deliberately — `qiskit-optimization` requires `qiskit<3`, and QAOA/COBYLA moved into
`qiskit_optimization` in 0.7.0, so tutorials importing them from `qiskit_algorithms` will fail.

```
qiskit==2.5.2   qiskit-aer==0.17.2   qiskit-optimization==0.7.0   scikit-learn   streamlit
```

Data: [UCI Statlog German Credit](https://archive.ics.uci.edu/dataset/144/statlog+german+credit+data)
(1000 applicants, 20 attributes), downloaded on first run to `data/`.
