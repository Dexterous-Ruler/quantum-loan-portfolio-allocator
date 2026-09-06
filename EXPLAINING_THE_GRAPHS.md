# Explaining the Output and Graphs to a Judge

**Team ASTITWA · Quantum-Assisted Loan-Portfolio Allocator**

> One page per visual. Each has: **what it shows** (one line), **how to read it**, **what to say**
> (a script you can speak), and **the question it triggers**. Numbers are the measured ones.
> Rule for every chart: say the *axes* first, then the *marker*, then the *takeaway*.

---

# PART 1 — The live 3D simulation

## 1.1 The four header numbers

| Number | What it means | Say |
| --- | --- | --- |
| **Customers** | How many borrowers are in the pool being decided | "Ten real customers from a 30,000-account dataset." |
| **Budget** | Capital available, in units of NT$20,000 | "The bank has 14 units — under half of what everyone is asking for, so it *must* choose." |
| **Qubits** | Size of the quantum problem | "Fourteen qubits: one per customer, plus four to encode the budget limit. This is the real problem size." |
| **Optimal profit** | The best achievable risk-adjusted profit | "This is the ground state — the single best book out of every possible combination." |

**Trigger question:** *"Why 14 qubits for 10 customers?"* → "The budget is an inequality — ≤ — and a quantum computer needs helper 'slack' qubits to encode that. Ten decisions plus four slack bits. The budget, not the customer count, drives the qubit count."

## 1.2 The floor (the 3D scene) — how to narrate it

**What it shows:** the optimiser's decision, as people.

- **On the stage, arms up, gold ring** → *funded.* "These are the ones the bank should lend to."
- **Standing back, faded** → *declined.* "Still creditworthy — just not the best use of limited capital."
- **Coin stack above each head** → how much capital they need (one coin = one unit). "Tall stack = big loan."
- **Red ring at the feet** → default risk from the AI model. "Brighter red = riskier."
- **Outfit colour** → customer segment (teal = university, burgundy = graduate, olive = high-school).
- **Beams between funded people** → the *quantum couplings*. Teal beam = same segment (appears when diversification is on); plum beam = opposite group (appears when fairness is on).

**Say:** *"Every person here is a real customer. The AI has already priced their risk — that's the red ring and the numbers you see on hover. The optimiser then chose who steps onto the stage. The beams are the actual interaction terms in our Hamiltonian: two people are coupled when funding both together affects diversification or fairness."*

**Trigger question:** *"What are the beams, really?"* → "Those are ZZ couplings. In the Ising Hamiltonian, a term Jᵢⱼ·ZᵢZⱼ links two qubits. Our diversification and fairness penalties are squared sums, and when you expand a square you get exactly those pairwise terms. The beam is a pair of coupled qubits drawn as geometry."

## 1.3 The readouts panel

| Readout | How to read | Say |
| --- | --- | --- |
| **Expected profit** | Sum of expected value of everyone funded | "Risk-weighted profit — each loan's interest if repaid, minus its loss if it defaults, weighted by how likely each is." |
| **Capital used** | Bar fills toward the budget | "The constraint binding. We use the whole budget because leftover capital earns nothing." |
| **Concentration** (Herfindahl) | 0 = perfectly spread, 1 = all in one segment. Green/amber/red pill | "How much of the book sits in one customer segment. Segments default together in a downturn, so a concentrated book is fragile." |
| **Approval gap (F − M)** | Approval rate of women minus men | "Positive means women approved more often. Near zero means fair. This is what the fairness switch controls." |
| **Diversifying cost / Fairness cost** (appears when a switch is on) | Profit given up vs. the unconstrained optimum | "We don't *claim* fairness — we **price** it. Here's exactly what parity cost in money." |
| **Greedy heuristic vs optimum** | How close a simple rule gets | "The rule a bank would actually use — fund by value-per-unit-of-capital — gets this close. It's our honest classical baseline." |

**The money line for the readouts:** *"Flip fairness on and the approval gap collapses from about 0.28 to 0.03, and the panel tells you it cost about 4% of profit. That's the whole idea — every rule becomes a number you can defend to a regulator."*

## 1.4 "You vs optimiser" (game mode)

**What it shows:** your hand-picked book next to the optimiser's.

**Say:** *"Try it — click people to fund them. Most people get to 85–90% of the optimum and can't find the last bit, because with ten customers there are 1,024 combinations and every extra customer doubles it. That's the problem we're solving, felt rather than explained."*

**Trigger question:** *"Isn't this just a puzzle?"* → "It's the puzzle a lender faces every day, scaled down to where a human can hold it. At 300 customers there are more combinations than atoms in the Earth."

---

# PART 2 — The two live charts

## 2.1 Profit across every budget (the area chart)

**What it shows:** the best achievable profit at *every* budget level, not just the current one.

**How to read:**
- **X axis:** capital budget, in units (left = small budget, right = large).
- **Y axis:** optimal expected profit at that budget.
- **The teal line:** solved exactly at each budget. **The gold dot:** where your slider is now. **The dotted line** drops to it.

**Say:** *"This is the optimiser run at every budget level. Two things to notice. First, it's not a straight line — it **bends over**. That's diminishing returns: the first units of capital fund the best customers, and each extra unit buys progressively less because what's left carries worse risk-adjusted value. Second, the gold dot is where we are right now — drag the slider and it walks along the curve."*

**Trigger question:** *"How is the curve computed?"* → "Exactly. For each budget we enumerate every feasible combination and take the true best. It's the same solver that finds the ground state, run fifteen times."

**Trigger question:** *"Where would a bank actually set the budget?"* → "Where the curve flattens — past that point, extra capital is better deployed elsewhere. The chart makes that knee visible."

## 2.2 Energy landscape — every possible portfolio (the big one)

**What it shows:** *every single way* to fund the pool, scored by the Hamiltonian's energy, sorted from best to worst.

**How to read:**
- **Each position along the X axis** is one complete portfolio — one of the 2ⁿ combinations (1,024 for ten customers).
- **Y axis is energy**, and **lower is better**. The teal area is the feasible portfolios.
- **The gold dot at the far left** is the **ground state**: the single lowest-energy configuration.
- **The grey band on the right** is every portfolio that breaks the budget — infeasible, pushed to the top by the penalty.
- **In game mode, a plum line marks *your* book** so you can see how far up the landscape you are.

**Say — this is the most important script in the whole demo:**
*"This chart is the quantum idea in one picture. We turn the business problem into an energy function — a Hamiltonian — where every possible loan book has an energy, and we build it so that lower energy means more profit. Then the problem 'find the best book' becomes 'find the lowest point on this landscape', which is the ground state — the gold dot. That's precisely what a quantum optimiser like QAOA is designed to do: find the ground state of a Hamiltonian. Everything to the right of the dot is a worse book; the grey region is books the bank can't even afford."*

**Then the honesty beat:**
*"At this size we can draw the whole landscape because there are only a thousand configurations — this page computes every one exactly. That's how we know the ground state for certain, and it's what we benchmark QAOA against in the Python backend. The landscape is exact; QAOA's job is to find that dot without seeing the whole picture."*

**Trigger question:** *"Why is the curve so steep at the left then flat?"* → "A handful of books are excellent, most are mediocre, and they cluster. That shape — a sharp drop to a narrow set of good answers — is exactly what makes the problem hard for a heuristic and interesting for a ground-state search."

**Trigger question:** *"What does the height of the grey band mean?"* → "Nothing physical — infeasible books are assigned a large penalty energy so the optimiser never picks them. It's the same trick the quantum formulation uses: constraints become energy penalties."

**Trigger question:** *"Is this what QAOA sees?"* → "No — and that's the point. QAOA never enumerates. It prepares a quantum state, tilts probability toward low-energy configurations, and samples. This chart is the ground truth we hold it to."

---

# PART 3 — The Deliverable-4 figures (deck and one-pager)

## 3.1 `quality.png` — Every QAOA run, by circuit depth

**What it shows:** the approximation ratio of every QAOA run, grouped by depth p = 1, 2, 3.

**How to read:** each dot is one run; the black bar is the mean per depth; the dashed red line is the greedy heuristic; the dotted line is the exact optimum (1.0).

**Say:** *"Look at the spread within a single depth versus the gap between depths. The dots within p=1 scatter more than the means differ across p=1, 2, 3. Within-cell scatter is 0.021; between-depth spread is 0.0036 — six times smaller. So the apparent 'best depth' is noise. Our first single-seed run said p=2 was best; rerunning said p=2 was worst. This chart is why we report three seeds per cell and refuse to name a best depth."*

**Trigger question:** *"So which depth should we use?"* → "We can't tell you at this scale, and anyone who claims to from one seed is reporting noise. We default to p=1 because it's cheapest and statistically indistinguishable."

## 3.2 `scaling.png` — The scaling wall

**What it shows:** wall-clock time vs. qubit count, for QAOA and exact search, on a log scale.

**Say:** *"Both grow with qubits, but classical exact search is two to three orders of magnitude faster at every size we can simulate. Beyond about 20 qubits the simulator itself falls off a cliff — 28 qubits needs 4 GB of memory, 30 needs 17 GB, more than the laptop has. That's the wall, and it's why we scoped the demo to 14."*

**Trigger question:** *"So quantum loses?"* → "At 14 qubits, yes, and we say so. The published crossover for QAOA on combinatorial problems is hundreds of qubits. We built the correct pipeline and measured where it stands today."

## 3.3 `fairness.png` — The price of parity

**What it shows:** for a sweep of fairness weights, the optimal book's profit against its approval-rate gap.

**How to read:** X = approval gap in percentage points; Y = expected profit; each point is an optimal portfolio at a different λ, labelled.

**Say:** *"Each point is a different setting of the fairness dial. Move right to left, the gap closes and profit falls. The curve is the exchange rate between fairness and money. We don't assert the model is fair — we hand you this curve and let the bank choose where to sit on it."*

## 3.4 `calibration.png` — Calibration

**What it shows:** predicted default probability vs. observed default rate, in bins.

**Say:** *"The dotted diagonal is perfect calibration — when the model says 30%, 30% actually default. Our curve hugs it. This matters more than accuracy here, because we multiply these probabilities by money: a 0.3 that should be 0.5 corrupts every coefficient in the Hamiltonian. Brier score 0.135."*

**Trigger question:** *"AUC 0.78 doesn't sound high."* → "For credit risk it's normal — human repayment is genuinely noisy. And ranking isn't our objective; calibration is, because the downstream optimiser consumes probabilities as cash."

## 3.5 `noise.png` — Noise sensitivity (present it as inconclusive)

**What it shows:** approximation ratio vs. depolarizing two-qubit gate error, with every individual run plotted behind the means.

**Say:** *"We swept gate error to ask 'would this survive real hardware?' The honest answer is our sweep can't tell you, and the chart shows why: the scatter of individual runs within a single error level is bigger than the movement between levels. We estimated it would take about 104 seeds per level — eight hours of noisy simulation — to resolve. Our three-seed pilot had told us eight seeds would do it; at twelve seeds we found the pilot had underestimated its own error bars. We report that rather than draw a curve through five noisy points."*

**Trigger question:** *"Why show an inconclusive result?"* → "Because a tidy descending curve would have looked better and been unsupported by our own data. This chart is evidence that the numbers we *do* claim are trustworthy."

---

# PART 4 — The ten-second version of each visual

If you only get one sentence per chart:

| Visual | One sentence |
| --- | --- |
| The floor | "Real customers; the ones on stage are who the optimiser funds; beams are the quantum couplings." |
| Profit vs budget | "The best profit at every budget — it bends over because extra capital buys progressively worse loans." |
| Energy landscape | "Every possible book as an energy; the lowest point is the ground state, and that *is* the optimal answer." |
| Quality by depth | "The spread within a depth is bigger than the gap between depths — so 'best depth' is noise." |
| Scaling wall | "Classical is 100× faster at every size we can simulate, and the simulator dies at ~30 qubits." |
| Price of parity | "The exchange rate between fairness and profit — we price it instead of claiming it." |
| Calibration | "When the model says 30%, 30% default — that's what we optimised for, because it's multiplied by money." |
| Noise | "Inconclusive, and we say so — the scatter beat the trend, and our pilot underestimated its own error bars." |

---

## The three rules that make chart explanations land

1. **Axes → marker → takeaway.** Always in that order. Never start with the conclusion.
2. **Point at the thing.** Physically point at the gold dot, the grey band, the knee in the curve.
3. **Lead with the loss on the comparison charts.** "Classical wins here" said first, confidently, is stronger than a judge discovering it.
