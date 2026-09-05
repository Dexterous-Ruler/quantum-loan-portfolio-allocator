# Judge Defense & Presentation Prep — Quantum-Assisted Loan-Portfolio Allocator

**Team ASTITWA · Tanishq Aryan · IEEE Quantum AI Hackathon 2026 · Theme 25**

> Read Part 1 until you can say it without looking. Skim Parts 2–4 twice. Keep Part 6 open
> during the demo. Every number here is measured and matches the repo, the deck and Deliverable 4.

---

## PART 1 — The core story (memorise this)

### The 15-second version
"A bank has more creditworthy customers than capital. Our AI model prices the risk of each
customer, and a quantum optimiser chooses which subset to actually fund under a budget."

### The 60-second version
"Classical credit scoring answers *how risky is this customer*. It does **not** answer *which
combination of customers should we fund* — and that second question is the real decision. It's a
0-1 knapsack: NP-hard, natively binary, natively quadratic. That's exactly what quantum
optimisation is built for.

So we do two things in **series**. First, a gradient-boosted model predicts each customer's
default probability. Then those probabilities become the coefficients of a QUBO, which becomes an
Ising Hamiltonian, which QAOA solves. The AI output literally *parameterises* the quantum problem
— remove the model and there's nothing left to optimise.

And we report the result honestly: at 14 qubits, classical still wins. We're not claiming a
speedup — we're demonstrating a correct end-to-end mapping and measuring exactly where it breaks."

### The one sentence that wins the room
**"We ran the quantum-vs-classical comparison honestly, classical won, and we're showing you that
result — because a fabricated quantum win is the thing that doesn't survive your first question."**

---

## PART 2 — The questions you listed, answered

### "Who are your competitors / what's the prior work?"
Three reference points, and we studied all of them:
- **Qiskit Finance `PortfolioOptimization` tutorial** — the canonical quantum portfolio example.
  It optimises asset weights with a mean-variance objective. We borrowed its **risk term** (see
  "extra things" below).
- **IBM Quantum Challenge portfolio notebooks** — same family, teaching material.
- **GitHub QAOA-portfolio repos** (e.g. Q-Folio and similar) — most use **CVaR aggregation**. We
  tested that (below) and did not adopt it because it didn't help on our problem.

The academic anchor is **Guerreschi & Matsuura, *Scientific Reports* 9:6903 (2019)** — "QAOA for
Max-Cut requires hundreds of qubits for quantum speed-up." That paper is *why* we don't claim
advantage at 14 qubits.

### "Why won't the prior work / existing approaches work here?"
Two distinct answers depending on what they mean:
- **The tutorials optimise a different thing** — asset weights on market returns. We optimise a
  *discrete fund/don't-fund decision on individual borrowers*, fed by a real risk model. That's a
  genuine hybrid pipeline, not a portfolio-weight demo.
- **The tabular quantum-classifier approach** (the shape of ~14 of the 25 hackathon themes) —
  project data into a quantum feature map, run a quantum kernel, compare accuracy. That's
  decorative: the kernel is a similarity function nobody can motivate, and it never beats a tuned
  classical model. We deliberately avoided that trap. Our quantum step solves a problem that is
  *natively* a quantum-optimisation problem, not a classification task wearing a quantum costume.

### "What framework did you use?"
- **Quantum:** Qiskit — `qiskit` 2.5.2, `qiskit-aer` 0.17.2 (simulator), `qiskit-optimization`
  0.7.0 (QUBO → Ising, QAOA, COBYLA).
- **AI:** scikit-learn (`HistGradientBoostingClassifier` + `CalibratedClassifierCV`).
- **Demo:** Streamlit. **Data:** pandas / numpy. **Plots:** matplotlib. **Tests:** pytest.
- **Version note that shows we know the ecosystem:** `qiskit-optimization` requires `qiskit<3`,
  and QAOA/COBYLA *moved into* `qiskit_optimization` at 0.7.0 — so tutorials importing them from
  `qiskit_algorithms` break. We pinned deliberately.

### "How are you sure it gives correct results?"
This is our strongest technical answer. Four independent guards:
1. **Ground truth by exhaustive search.** At 14 qubits we can enumerate all 2ⁿ feasible subsets
   and find the *true* optimum. Every QAOA result is scored against it — approximation ratio 1.0
   means it found the exact best answer.
2. **The QUBO is verified against that ground truth.** Our load-bearing test,
   `test_bruteforce_matches_qubo_diagonalisation`, asserts that brute-force enumeration and exact
   diagonalisation of the QUBO agree. If the penalty weights were wrong, they'd disagree and every
   downstream number would be meaningless. **This test caught a real bug** — a fairness-group
   label updated in one place but missed in the QUBO builder, which silently turned the fairness
   term into a constant. Nothing crashed; only the test caught it.
3. **22 automated tests + GitHub Actions CI**, run on every push.
4. **Every number in our comparison is generated from measured CSVs** — nothing is typed by hand,
   so a slide cannot drift from the experiment. A fresh clone regenerates byte-identical output.

### "What datasets did you use, and how?"
**UCI *Default of Credit Card Clients* (Taiwan, 2005)** — 30,000 real accounts, 23 predictors,
**real 22.1% default rate**. Split 21,000 train / 9,000 test.
- **How:** the model trains on payment history + bill/payment amounts to predict `P(default)`.
  Each probability becomes an expected value: `EV = P(repay)·interest − P(default)·LGD·exposure`.
  Those EVs are the linear coefficients of the QUBO. So the dataset flows: raw features → model →
  probabilities → money → quantum problem.
- **Exposure detail (shows domain awareness):** it's revolving credit, so exposure at default is
  the outstanding *balance* clipped to the credit limit — not the limit. Using the limit would
  overstate every position ~10×.

### "Why did you switch datasets / why not German Credit?"
We started on UCI German Credit — the standard benchmark — and moved off it on purpose:
- 1,000 rows from **1973–75**; ours is 30,000 from 2005.
- German Credit's 30% default rate is a **stratified over-sample** (700/300 by construction), not
  a real rate — it inflated every money figure.
- **Decisive:** its sex attribute is mis-coded. Grömping (2019) showed male singles and female
  non-singles share code A92, and A95 (female:single) has **zero rows** in the published file — so
  any "female" group is a mixed bag, and a fairness result on it measures nothing. Most published
  fairness work on that dataset uses exactly that broken variable. We caught it and moved.

### "What extra did you do beyond the four deliverables?"
Five things most teams won't have:
1. **A real risk term.** We added a Herfindahl concentration penalty so the objective is genuine
   mean-variance portfolio optimisation, not a bare knapsack. Costs **zero extra qubits**.
2. **Fairness as a constraint, not a paragraph.** Approval-rate parity is a penalty *in the
   objective* — we can *price* it: the gap closes from ~0.28 to ~0.03 for about 4% of profit.
3. **Four ablation studies** — depth, noise, pricing sensitivity, and CVaR — each held to a
   statistical noise-floor test.
4. **We audited our own results and retracted three claims** (see Part 4). This is the headline.
5. **Engineering:** 22 tests, CI, and fully reproducible generated deliverables.

### "What is it deployed on?"
- **Runs on:** Qiskit Aer statevector simulator, on a laptop CPU. No quantum hardware, no cloud
  quantum queue — the brief specifies "small qubit counts, simulator only," and we stayed inside
  that deliberately.
- **The demo app:** a Streamlit web app. Locally it runs at `localhost:8899`; for a public link
  it deploys to Streamlit Community Cloud from the public GitHub repo (the app reads pre-computed,
  committed artifacts so it starts instantly without retraining).
- **Code:** public GitHub repo, github.com/Dexterous-Ruler/quantum-loan-portfolio-allocator.
- **If asked about real hardware:** "We characterised it — a depolarizing-noise sweep in the repo.
  The honest answer is our sweep is inconclusive at the seed count we could afford, and we say so."

---

## PART 3 — Every number, ready to quote

### The AI model
| | |
| --- | --- |
| Model | Calibrated gradient-boosted classifier (HistGBM + Platt) |
| ROC-AUC | **0.780** |
| Brier score | **0.135** (the metric we optimise — calibration matters, it's multiplied by cash) |
| Baseline (tuned logistic regression) | AUC 0.715 |
| Train / test | 21,000 / 9,000 |
| Positive-EV candidate pool | 6,104 of 9,000 |

*If asked why GBM beats logistic regression here but not on German Credit: "Boosting needs data.
At 1,000 rows the linear model won; at 21,000 rows boosting wins. We report both."*

### The quantum module
| | |
| --- | --- |
| Algorithm | QAOA (cost + mixer layers, COBYLA outer loop, 2,048 shots) |
| Qubits (default) | **14** = 10 decisions + 4 budget-slack bits |
| Formula | qubits = n + ceil(log₂(budget+1)) |
| Pauli terms | 105 |
| Transpiled depth / 2-qubit gates | 78 / 182 |
| Simulator | Qiskit Aer |

### The comparison (the honest headline)
| Solver | Approx ratio | Hits exact optimum | Time |
| --- | --- | --- | --- |
| Exact (brute force) | 1.0000 | 100% | 0.06 s |
| **Greedy heuristic** | **0.9986** | **87.5%** | 0.0002 s |
| QAOA (pooled) | 0.9789 | 55.6% | 7.5 s |

**QAOA is ~125× slower than exhaustive search and loses to the greedy heuristic on both metrics.**

### Fairness / diversification
- Fairness penalty: approval-rate gap ~0.28 → ~0.03 for ~4% of profit.
- Both penalties add **zero** qubits (squared linear forms).

### Scaling wall
14 qubits fine; 28 = 4.3 GB; 30 = 17.2 GB (dead on a 16 GB laptop). Statevector = 2ⁿ × 16 bytes.

---

## PART 4 — The self-audit (this is what sets you apart — lead with it)

"We didn't just build it — we tried to break our own results. Three times we found a claim that
looked good and didn't survive scrutiny, and we retracted it."

1. **Depth ranking is noise.** Scatter within one (instance, depth) cell across seeds is 0.0211;
   spread between depths is 0.0036 — 6× smaller. Our first single-seed run said p=2 was best;
   re-running said p=2 was worst. So we report 3 seeds per cell and *don't* claim a best depth.
2. **A metric that lied.** Our first noise study showed noise making QAOA *better* — impossible.
   Cause: "best of 2,048 shots" hits the optimum by chance even from a near-random distribution.
   We switched to a distribution-level metric that can actually respond to noise.
3. **The power calculation was itself under-powered.** A 3-seed pilot estimated ~8 seeds would
   settle the noise trend. At 12 seeds the scatter came out 2.5× bigger and the requirement jumped
   to ~104 seeds (~8 hours). The pilot had underestimated its own error bars. We report the sweep
   as inconclusive rather than drawing a fake curve.

**Why this matters (say this):** "Every one of these would have made a nicer slide if we'd left it
in. We took them out. That's the reason you can trust the numbers we *did* keep."

---

## PART 5 — Hard / trap questions

**"So quantum is useless here?"**
"At this scale, for speed, yes — and we say so. But we've built the exact pipeline that *would*
benefit once hardware crosses the few-hundred-qubit line the literature points to. The value today
is the correct mapping and the honest scaling measurement, which is what the brief asked for."

**"Isn't this just a knapsack you could solve in 60 milliseconds classically?"**
"Yes, at n=10 — that's precisely why our comparison shows classical winning. We're not hiding
that. We're demonstrating the quantum *formulation* is correct and measuring where it stops being
simulable, not claiming it's faster."

**"Where is the quantum actually doing something?"**
"The QUBO becomes a real 14-qubit Ising Hamiltonian — 105 Pauli terms, depth 78, 182 two-qubit
gates. QAOA prepares a parameterised state and we measure it. The fairness and risk penalties
create genuine ZZ couplings between specific customers. It's a real circuit, not a wrapper."

**"Did you compare against a *strong* classical baseline or a strawman?"**
"The strongest possible: exhaustive enumeration gives the true optimum, and we also include the
greedy heuristic a bank would actually deploy. QAOA loses to both. No strawman."

**"How do you know your model isn't biased?"**
"We don't claim it's unbiased — we *measure and price* bias. Sex is excluded from the features, and
approval-rate parity is a tunable penalty in the optimiser. We can show you the exact profit cost
of closing the gap. That's more honest than asserting fairness."

**"Why should we trust a 22% number / this dataset?"**
"It's 30,000 real accounts with a real default rate, unlike the standard benchmark whose rate is
manufactured. We even documented the coding bug that made us leave that benchmark."

**"What happens if the demo breaks live?"**
Have the demo GIF (`artifacts/demo.gif`) and the one-page PDF open in tabs. "Here's a recording of
the exact interaction" — never dead air.

**"What would you do with more time / real hardware?"**
"Run the noise sweep to the ~104 seeds needed to resolve it, and scale the pool toward the
few-hundred-qubit regime where QAOA's crossover is expected. The pipeline is already built for it."

**"What was the hardest part?"**
"Resisting the temptation to fake a quantum win. Every honest measurement pushed us toward
'classical wins,' and the discipline was in reporting that clearly instead of cherry-picking a
lucky seed — which our own ablations proved is exactly how you'd fool yourself."

---

## PART 6 — Live demo runbook (keep open during the talk)

**Before you present:**
1. Start the app; open `localhost:8899` (or the Streamlit Cloud URL).
2. Press **Optimise** once on the default config so it's cached — first run is ~6 s, then instant.
3. Click each config you plan to show once, so none pauses live.
4. Open two backup tabs: `DELIVERABLE_4.html` (the PDF) and `artifacts/demo.gif`.

**The 8 demo beats (≈3 min):**
1. Open the "What is this" panel — read the one-liner.
2. Point at the metric row: "10 customers, **14 qubits** — the real problem size."
3. Section 1: "The AI priced every customer; these numbers become the quantum coefficients — in
   **series**."
4. Press **Optimise** — "QAOA just searched a 14-qubit Hamiltonian."
5. Drag the **budget slider** — "watch the dot move along the profit curve, diminishing returns."
6. Toggle **Diversify** — "concentration drops, and we can tell you what it *cost*."
7. Toggle **Fairness** — "gap 0.28 → 0.03 for ~4% of profit. We don't claim fair — we *price* it."
8. Section 4 + **The circuit** tab — "classical wins, we're honest about it; and here's the real
   14-qubit / depth-78 circuit."

---

## PART 7 — Final checklist before you walk in

**Submission (IEEE form):**
- [ ] Repo is public ✅ (already done)
- [ ] Google Form: switch account to your email, fill mobile / IEEE# / institution
- [ ] Live-demo link (Streamlit Cloud URL) in the form
- [ ] Demo video → Drive folder → shared "Anyone with the link"
- [ ] Upload `DELIVERABLE_4.html` as PDF + `PRESENTATION.pptx`
- [ ] Tick the 3 certifications
- [ ] Submit before 5:00 pm

**Presentation:**
- [ ] Deck (`PRESENTATION.pptx`) reviewed; you can speak each slide's speaker note
- [ ] Demo pre-warmed, backup GIF + PDF tabs open
- [ ] Part 1 memorised; Parts 4 & 5 skimmed twice
- [ ] Repo link and one key stat (AUC 0.780, 14 qubits, 125× slower) on the tip of your tongue

**The three things to say out loud, unprompted:**
1. "The AI and quantum modules run in **series** — remove the model and there's no quantum problem."
2. "We're reporting a **negative result**, and that's the point — it's trustworthy *because* it
   didn't come out the way we wanted."
3. "We caught our own first benchmark being wrong — three times — and fixed it."

**The three things never to say:**
1. Never claim a quantum speedup (your own page contradicts it).
2. Never say the model is "fair" — say you can *price* parity.
3. Never quote absolute profit as a real P&L — it's one 10-account slice of a 2005 card book.
