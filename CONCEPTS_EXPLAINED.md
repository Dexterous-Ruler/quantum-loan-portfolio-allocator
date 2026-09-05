# Understand Your Own Project — Every Concept From Zero

**Team ASTITWA · Quantum-Assisted Loan-Portfolio Allocator**

> This assumes you know **nothing** about quantum computing, optimisation, or ML. Read it
> top to bottom once. Each concept has three parts: **What it is** (plain), **In our project**
> (how we use it), and **If a judge asks** (the sentence to say). By the end you will be able
> to defend every word in the deck as your own.

---

## The whole project in five plain sentences

1. A bank can lend to more people than it has money for, so it must **choose the best group** of
   borrowers to fund.
2. We use an **AI model** to predict how likely each borrower is to not pay back.
3. We turn those predictions into **"expected profit per borrower."**
4. We hand that to a **quantum algorithm** that picks the most profitable group that fits the
   budget — while spreading risk and staying fair.
5. We honestly checked it against normal computers and reported that, at this small size, the
   normal computer still wins — because a truthful result is what survives tough questions.

Everything below explains the words in those five sentences.

---

# PART A — The problem we are solving

## A1. The knapsack problem (and "0-1")

**What it is:** Imagine a backpack that can hold 10 kg. You have many items, each with a *weight*
and a *value* (worth in money). You want to pick items that give the **most total value without
going over 10 kg**. That is the *knapsack problem*.
**"0-1"** means each item is either taken (1) or left (0) — you cannot take half an item.

**In our project:** the "backpack" is the bank's capital budget. Each "item" is a loan applicant.
The "weight" is how much money the loan needs; the "value" is the expected profit from that loan.
We pick the set of applicants with the most total profit that fits the budget.

**If a judge asks:** *"It's a 0-1 knapsack problem — pick the best subset of items that fits a
capacity limit, where each item is all-or-nothing. Here the items are loan applicants and the
capacity is the capital budget."*

## A2. Why it's "NP-hard"

**What it is:** For a hard problem like knapsack, there is no known shortcut that stays fast as
the problem grows. With *n* items there are **2ⁿ** possible combinations. 10 items = 1,024
combinations (easy). 50 items = a quadrillion. 300 items = more combinations than atoms in the
Earth. "NP-hard" is the formal label for "gets explosively hard as it grows."

**In our project:** at our size (10 items = 2¹⁰ = 1,024) we can still check every combination by
brute force, which is *how we know the true best answer*. That only works because we kept it small.

**If a judge asks:** *"NP-hard means the number of possible answers grows as 2 to the power n, so
brute force becomes impossible at scale. That growth is exactly why people hope quantum
optimisation will help on large instances."*

## A3. Why quantum is a *reasonable* fit here (not decoration)

**What it is:** Quantum optimisation algorithms are built for problems that are (a) made of
yes/no choices and (b) where choices interact. Knapsack-with-penalties is exactly that shape.

**In our project:** every decision is fund/don't-fund (yes/no = binary), and our risk and fairness
rules make choices interact (funding two similar customers is worse than funding two different
ones). That "binary + interacting" structure is what maps cleanly onto a quantum computer.

**If a judge asks:** *"Our problem is natively binary and natively quadratic — yes/no decisions
that interact in pairs. That's the exact structure a quantum optimiser encodes, unlike a
classification task, where quantum is just decoration."*

---

# PART B — The AI side

## B1. A classifier and "P(default)"

**What it is:** A *classifier* is a model that looks at facts about something and outputs a
probability. Here it reads a customer's history and outputs **P(default)** — the probability
(0 to 1) that they will fail to repay.

**In our project:** we train it on 30,000 real customers where we *know* who defaulted, so it
learns the patterns. Then it scores new customers.

**If a judge asks:** *"It's a supervised classifier that outputs a calibrated default probability
per customer from their payment history."*

## B2. Gradient boosting (the model we chose)

**What it is:** A way of building a strong predictor out of many tiny, weak decision rules. It
builds one small rule, sees where it's wrong, builds another rule to fix those mistakes, and
repeats hundreds of times. "Gradient boosting" = each new rule is aimed at the current errors.
We use scikit-learn's `HistGradientBoostingClassifier`.

**In our project:** it beat plain logistic regression on this data (AUC 0.780 vs 0.715) because
we had 21,000 training rows — boosting needs a lot of data to shine.

**If a judge asks:** *"Gradient-boosted decision trees — an ensemble that adds many small trees,
each correcting the previous ones' errors. We picked it because it beat a tuned linear baseline
on 21,000 rows."*

## B3. AUC (how good the model is at ranking)

**What it is:** AUC = "Area Under the ROC Curve." One number from **0.5 to 1.0**. It answers:
*if I pick one real defaulter and one real non-defaulter at random, how often does the model
correctly say the defaulter is riskier?* **0.5 = coin flip (useless). 1.0 = perfect.** ~0.78 is
solid for credit scoring (this problem is genuinely noisy — humans aren't perfectly predictable).

**In our project:** our model scores **AUC 0.780**.

**If a judge asks:** *"AUC is the probability the model ranks a random defaulter above a random
non-defaulter. 0.5 is random, 1.0 perfect; ours is 0.78, which is normal for credit risk."*

## B4. Brier score and calibration (why we care more about this than AUC)

**What it is:** *Calibration* means the numbers are literally true: of everyone the model says is
"30% likely to default," about 30% actually do. The **Brier score** measures this — it's the
average squared gap between the predicted probability and what actually happened (0 or 1). **Lower
is better**; ours is **0.135**.

**Why it matters more here:** we don't just *rank* customers — we **multiply their probability by
money**. If the model says 0.3 but the truth is 0.5, every downstream profit number is wrong. So a
well-calibrated model matters more than a slightly higher AUC.

**If a judge asks:** *"Brier score measures calibration — whether a predicted 30% really means
30%. We optimise for it because we multiply these probabilities by cash, so being well-calibrated
matters more than raw ranking. Ours is 0.135."*

## B5. Expected value, LGD, and exposure (turning probability into money)

**What it is — the key formula:**
```
EV = P(repay) × interest_earned  −  P(default) × LGD × exposure
```
- **EV** = expected value = the average profit from this loan, accounting for risk.
- **P(repay) = 1 − P(default).**
- **interest_earned** = what the bank makes if they pay back (we assume 18% APR).
- **LGD** = "Loss Given Default" = the fraction of money you lose when a loan goes bad. Not 100%,
  because you often recover some. We assume **60%**.
- **exposure** = how much money is actually at risk = the outstanding balance (capped at the
  credit limit).

**In one line:** *"what I gain if they pay, minus what I lose if they don't, weighted by how
likely each is."*

**In our project:** this EV is the "value" of each item in the knapsack. It's the bridge from the
AI model to the quantum problem — the model gives P(default), this formula turns it into money.

**If a judge asks:** *"Expected value = probability-of-repay times interest, minus
probability-of-default times loss-given-default times exposure. LGD is the fraction lost on a bad
loan; exposure is the balance at risk. This is how the model's probabilities become the numbers
the optimiser maximises."*

---

# PART C — The bridge: QUBO

## C1. What QUBO means

**What it is:** QUBO = **Q**uadratic **U**nconstrained **B**inary **O**ptimization. Break it down:
- **Binary** — every variable is 0 or 1 (fund / don't fund).
- **Quadratic** — the formula can multiply two variables together (xᵢ·xⱼ), which lets choices
  *interact* in pairs.
- **Unconstrained** — there are no separate "rules"; every rule is folded *into* the single
  formula as a penalty (see C2).
- **Optimization** — we're minimising (or maximising) that one formula.

So a QUBO is **one maths expression, in yes/no variables, that can pair them up, and whose best
setting is the answer.** It is the standard "input format" that quantum optimisers accept.

**If a judge asks:** *"QUBO is Quadratic Unconstrained Binary Optimization — a single objective
over 0/1 variables with pairwise interaction terms. It's the canonical form a quantum optimiser
takes, so our whole job is to write our problem as one QUBO."*

## C2. "Constraints become penalties" (how the budget and fairness get in)

**What it is:** A QUBO has no separate rules, so anything we *require* has to be rewritten as a
**cost you pay for breaking it**. Go over budget? Add a big penalty. Concentrate too much in one
segment? Add a penalty. Approve one group much more than another? Add a penalty. The optimiser
then avoids those because they hurt the score.

**In our project, our full objective is:**
```
maximise:  Σ EVᵢ·xᵢ          (total expected profit)
         − γ · concentration(x)   (diversification penalty)
         − λ · parity_gap(x)²     (fairness penalty)
subject to: Σ unitsᵢ·xᵢ ≤ budget  (capital limit → penalty)
```
- **γ (gamma)** controls how much we care about spreading risk.
- **λ (lambda)** controls how much we care about fairness.
- The budget limit is turned into a penalty using extra helper bits (this is what costs qubits —
  see D2).

**The clever bit:** both the concentration and fairness penalties are *squared* terms, which makes
them **quadratic** — so they slot into the QUBO for **free (zero extra qubits)** while making the
problem genuinely "interacting."

**If a judge asks:** *"A QUBO is unconstrained, so we express the budget, diversification, and
fairness as penalty terms added to the objective. The optimiser avoids breaking them because they
cost score. The fairness and risk penalties are squared-linear, so they add zero qubits."*

## C3. Herfindahl concentration (the diversification rule)

**What it is:** A standard way to measure "are all your eggs in one basket?" You take each group's
share of the total, square it, and add up. If everything is in one group the number is 1 (bad); if
it's spread evenly it's small (good). Banks use it for exactly this.

**In our project:** groups = customer segments. The penalty pushes the optimiser to fund a *mix*
of segments, because segments tend to default together in a downturn.

**If a judge asks:** *"The Herfindahl index — sum of squared segment shares — is the standard
concentration measure. We penalise it so the optimiser diversifies instead of piling into one
segment."*

---

# PART D — The quantum side

## D1. A qubit (one sentence)

**What it is:** A normal bit is 0 or 1. A **qubit** can be in a combination of both at once
(*superposition*) until you measure it, at which point it collapses to 0 or 1. *n* qubits can
represent all 2ⁿ combinations simultaneously — that's the resource quantum algorithms exploit.

**If a judge asks:** *"A qubit holds a superposition of 0 and 1, so n qubits span all 2ⁿ
combinations at once; measurement collapses it to one bitstring."*

## D2. Why our problem needs 14 qubits

**What it is:** one qubit per yes/no decision. We have **10 applicants → 10 qubits.** The budget
limit ("≤ B") needs extra "slack" qubits to encode an *inequality* as a penalty — that adds
**4 more → 14 total.** The formula is `qubits = n + ceil(log₂(budget+1))`.

**In our project:** 14 qubits, and the budget is the reason it's not just 10. Making the budget
coarser (fewer possible values) is the single lever that keeps the qubit count low.

**If a judge asks:** *"Ten decision qubits plus four slack qubits to encode the budget inequality
as a penalty — fourteen total. The slack is why the budget, not the applicant count, drives the
qubit budget."*

## D3. The Ising Hamiltonian and "ZZ couplings"

**What it is:** A *Hamiltonian* is just an **energy formula** — it assigns an energy number to
every possible configuration of the qubits. The **Ising** form is a specific, physics-standard
energy formula:
```
H = Σ hᵢ Zᵢ  +  Σ Jᵢⱼ Zᵢ Zⱼ
```
- **Zᵢ** is a measurement on qubit *i* that gives +1 or −1.
- **hᵢ Zᵢ** = a "field" term: an energy cost depending on a *single* qubit.
- **Jᵢⱼ Zᵢ Zⱼ** = a **coupling** term: an energy cost depending on a *pair* of qubits together.
  These are the **"ZZ couplings."**

We convert our QUBO (0/1 variables) into this Ising form (±1 spins) with a simple substitution
`x = (1 − Z)/2`. It's the same problem in the language a quantum computer speaks.

**In our project:** our Ising Hamiltonian has **14 qubits and 105 Pauli terms**. The single-qubit
terms come from each applicant's expected value; the ZZ coupling terms come from the fairness and
concentration penalties — i.e. two *specific* applicants are "coupled" because funding both affects
fairness or concentration.

**If a judge asks:** *"A Hamiltonian is an energy function over the qubits. The Ising form has
single-qubit field terms and two-qubit ZZ coupling terms. We map our QUBO to it; the single terms
carry each applicant's value, the ZZ couplings carry the fairness and risk interactions."*

## D4. Ground state = the answer (this is the "key state" you asked about)

**What it is:** Every configuration of qubits has an energy (from the Hamiltonian). The
**ground state** is the configuration with the **lowest energy**. (A configuration is also called
an *eigenstate*; the ground state is the lowest-energy eigenstate.)

**The whole trick of quantum optimisation:** we *deliberately build* the Hamiltonian so that its
lowest-energy configuration is exactly the best loan portfolio. **Find the ground state → read off
the bitstring → that's the answer.** "Minimise energy" and "maximise profit" are the same thing
because we set it up that way.

**If a judge asks:** *"The ground state is the lowest-energy configuration of the Hamiltonian. We
construct the Hamiltonian so its ground state encodes the optimal portfolio — so solving the
problem becomes finding the ground state, and the winning bitstring is the set of loans to fund."*

## D5. QAOA — step by step (the algorithm itself)

**What it is:** QAOA = **Q**uantum **A**pproximate **O**ptimization **A**lgorithm. Its job is to
*find (approximately) the ground state* of our Hamiltonian. Here is the full loop, in order:

1. **Start** all qubits in an equal superposition of every possible bitstring (all answers at once).
2. **Cost layer** — apply `e^(−iγ·H_C)`, an operation built from our cost Hamiltonian. It "tilts"
   the superposition to favour lower-energy (better) answers. **γ (gamma)** controls how hard.
3. **Mixer layer** — apply `e^(−iβ·H_B)`, built from a simple "mixer" Hamiltonian (just X-flips).
   It shuffles probability between answers so the search doesn't get stuck. **β (beta)** controls
   how much.
4. **Repeat** the cost+mixer pair **p** times (`p` = "depth" or "reps"; we mostly use p=1). More
   layers = more expressive but harder to tune. So there are **2p tuning numbers** (γ's and β's).
5. **Measure** the qubits **2,048 times** ("shots"). Each measurement gives one bitstring = one
   candidate portfolio. Better answers come up more often.
6. **A classical optimiser (COBYLA)** looks at the average energy of those measurements and
   **adjusts γ and β** to push it lower, then we go back to step 1. This repeats until it settles.
7. **Output** the best feasible bitstring seen.

So QAOA is a **hybrid** loop: a quantum circuit proposes answers, a classical optimiser tunes the
knobs. That's normal — QAOA is *designed* to be quantum + classical together.

**If a judge asks "how does QAOA work?":** *"It prepares an equal superposition, then alternates a
cost layer that favours good answers and a mixer layer that keeps the search moving, p times. A
classical optimiser, COBYLA, tunes the layer angles to minimise the measured energy. We sample
2,048 shots and take the best feasible bitstring. It's a hybrid quantum-classical loop."*

## D6. The pieces of QAOA, defined

- **Cost Hamiltonian (H_C):** our problem's energy formula (Part D3). Encodes what we want.
- **Mixer Hamiltonian (H_B):** a simple standard operator (sum of X gates) that moves the search
  around. Not problem-specific.
- **γ, β (gamma, beta):** the tunable angles — how strongly to apply each layer. QAOA's whole job
  is finding good values for these.
- **p / reps / depth:** how many cost+mixer pairs. We use p=1 by default (and showed deeper isn't
  reliably better at our scale — see the "self-audit" story).
- **COBYLA:** the classical optimiser that tunes γ and β. ("Constrained Optimization BY Linear
  Approximation" — you don't need the full name, just "the classical tuner.")
- **Shots (2,048):** how many times we measure the final circuit to sample candidate answers.
- **Aer simulator:** we *simulate* the quantum computer on a normal laptop (Qiskit Aer). No real
  quantum hardware — the brief said "simulator only."

## D7. Approximation ratio (how we grade QAOA)

**What it is:** `approximation ratio = (value QAOA found) / (true best value)`. **1.0 means it
found the exact optimum.** 0.98 means it got 98% of the best achievable profit.

**In our project:** QAOA averages **0.9789** — very close, but the greedy classical heuristic
averages **0.9986** and is ~125× faster. So QAOA is good but not winning here, and we say so.

**If a judge asks:** *"Approximation ratio is what you found over the true optimum; 1.0 is perfect.
QAOA gets 0.979, the classical greedy gets 0.999 — so classical wins at this scale, which we report
honestly."*

---

# PART E — Why our specific choices

## E1. Why the Taiwan dataset (and not an Indian one)?

**Straight answer:** we needed a dataset that is (1) **real**, (2) **large**, (3) **public and
citable** so judges can verify it, (4) has a **real default label**, and (5) has a **cleanly-coded
protected attribute** (sex) so our fairness feature is meaningful. The **UCI "Default of Credit
Card Clients" (Taiwan, 2005)** ticks all five: 30,000 real accounts, a real 22.1% default rate, a
recognised benchmark, unambiguous demographics.

**On India specifically:** there is **no equivalent large, public, standard Indian retail-credit
dataset** with a real default label and a clean protected attribute that we could cite and let
judges reproduce. Indian lending data is either proprietary (banks don't release it),
aggregate/synthetic (Kaggle toy sets), or lacks the demographic field the fairness work needs. We
chose reproducibility over locale. **Crucially, our pipeline is dataset-agnostic** — swap in any
CSV with the same columns and everything downstream (model → EV → QUBO → QAOA) runs unchanged. If a
bank gave us Indian data tomorrow, it's a one-file change.

**If a judge asks:** *"We needed a real, large, public, citable dataset with a clean protected
attribute so our fairness result is meaningful and reproducible. No Indian dataset meets all five
publicly. The Taiwan UCI set does. And our pipeline is dataset-agnostic — the same code runs on
any bank's data with these columns."*

## E2. Why not the German Credit dataset (the "obvious" one)?

We started there — it's *the* standard credit benchmark — and moved off it for three reasons:
1. **Too small and too old:** 1,000 rows from 1973–75.
2. **Fake default rate:** its 30% rate is a *stratified over-sample* (700 good / 300 bad *by
   construction*), not a real rate — so all money figures were distorted.
3. **Broken fairness variable (decisive):** its sex code is documented as wrong (Grömping 2019) —
   two different groups share one code, and one group has zero rows. Any "fairness" result on it
   measures nothing. **We caught this and switched** — that itself is a point in our favour.

**If a judge asks:** *"German Credit is the usual benchmark but it's 1,000 rows from the 1970s, its
default rate is a constructed over-sample, and its sex coding is documented as broken — so a
fairness result on it is meaningless. We moved to a real, larger, correctly-coded dataset."*

## E3. Why simulator only / why 14 qubits?

**What it is:** the hackathon brief says "small qubit counts, simulator only." Real quantum
hardware today is noisy and access is queued; simulating 14 qubits on a laptop is exact, instant,
and reproducible. And 14 qubits is deliberate — big enough to be a real Ising problem, small
enough that we can *also* brute-force the true answer to check QAOA against.

**If a judge asks:** *"Simulator, per the brief — it's exact and reproducible. Fourteen qubits is
the sweet spot: a genuine Ising instance we can still verify by brute force. Above ~30 qubits a
laptop can't simulate it, which we measured."*

## E4. Why the honest "classical wins" result instead of claiming a quantum win?

**What it is:** at 14 qubits, quantum optimisation genuinely isn't faster or better than classical
— the known crossover is *hundreds* of qubits (Guerreschi & Matsuura 2019). We could have shown a
cherry-picked lucky run, but our own tests proved that's how you fool yourself. So we report the
truth: correct method, honestly measured, classical wins today.

**If a judge asks:** *"We're not claiming a speedup because there isn't one at 14 qubits — the
literature puts the crossover at hundreds. We built the correct pipeline and measured where it
stands. A fabricated win wouldn't survive your questions; a correct method and an honest number
will."*

---

# PART F — Rapid-fire "what is / why" drill

Cover the right column and try to answer from memory.

| If they ask… | One-line answer |
| --- | --- |
| What is a QUBO? | One quadratic formula in 0/1 variables whose best setting is the answer — the input format quantum optimisers take. |
| What is a knapsack problem? | Pick the highest-value subset of items that fits a capacity limit. |
| What does 0-1 mean? | Each item is all-or-nothing — fund or don't fund, no fractions. |
| What is QAOA? | A hybrid quantum-classical algorithm that finds the approximate lowest-energy state of our problem Hamiltonian. |
| What is a Hamiltonian? | An energy formula that scores every configuration of the qubits. |
| What is the ground state? | The lowest-energy configuration — we build things so it's the optimal portfolio. |
| What are ZZ couplings? | Energy terms linking two qubits — here, two applicants coupled by the fairness/risk penalties. |
| What is γ and β? | The tunable angles of QAOA's cost and mixer layers; COBYLA tunes them. |
| What are shots? | How many times we measure the circuit to sample candidate answers (2,048). |
| What is AUC? | Probability the model ranks a real defaulter above a non-defaulter; 0.5 random, 1.0 perfect, ours 0.78. |
| What is Brier score? | How well-calibrated the probabilities are (lower better, ours 0.135). |
| What is calibration? | When "30% risk" really means 30% default — matters because we multiply by money. |
| What is LGD? | Loss Given Default — fraction of money lost on a bad loan (we use 60%). |
| What is expected value here? | P(repay)×interest − P(default)×LGD×exposure — profit weighted by risk. |
| What is the Herfindahl index? | Sum of squared segment shares — a standard concentration measure. |
| What is the approximation ratio? | Found value ÷ true optimum; 1.0 is perfect (ours 0.979). |
| Why simulator? | Brief requires it; exact, reproducible, no hardware queue. |
| Why 14 qubits? | 10 decisions + 4 budget-slack bits; small enough to verify by brute force. |
| Why Taiwan data? | Real, large, public, citable, clean protected attribute; no Indian set meets all five publicly; pipeline is dataset-agnostic. |
| Why does classical win? | Quantum's crossover is hundreds of qubits; at 14 we honestly report classical is better. |

---

# PART G — 30-second glossary

- **Qubit** — quantum bit; 0 and 1 at once until measured.
- **Superposition** — being in many states at once.
- **Hamiltonian** — energy formula over the qubits.
- **Ising model** — the standard "spins + couplings" energy formula.
- **Ground state** — lowest-energy configuration = our answer.
- **QUBO** — Quadratic Unconstrained Binary Optimization; our problem's format.
- **QAOA** — the quantum+classical algorithm that solves the QUBO.
- **Cost / mixer layer** — the two alternating steps inside QAOA.
- **γ, β** — QAOA's tunable angles.
- **COBYLA** — the classical optimiser tuning those angles.
- **Shots** — number of measurements taken.
- **Aer** — Qiskit's simulator (runs the "quantum computer" on a laptop).
- **Knapsack / 0-1** — pick the best subset under a capacity limit, all-or-nothing.
- **NP-hard** — gets exponentially harder with size (2ⁿ combinations).
- **Classifier** — model that outputs a probability from features.
- **Gradient boosting** — ensemble of small trees, each fixing prior errors.
- **AUC** — ranking quality, 0.5–1.0.
- **Brier score** — calibration quality, lower better.
- **Calibration** — predicted % matches real % .
- **LGD** — loss given default.
- **Exposure** — money at risk (the balance).
- **Expected value (EV)** — risk-weighted profit per loan.
- **Herfindahl index** — concentration measure.
- **Approximation ratio** — how close to the true best answer.

---

## How to study this before tomorrow

1. Read the five sentences at the top until you can say them.
2. Read Parts A–D once slowly — that's the real learning.
3. Cover the right column of Part F and quiz yourself. If you can answer 15 of 20, you're ready.
4. The three you MUST nail: **what a QUBO is, what QAOA does, and why classical wins.** Those are
   the questions a technical judge always asks.
