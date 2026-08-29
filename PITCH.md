# Demo script + judge Q&A

## The 3-minute run

**0:00 — The problem in one sentence.**
"A bank has more creditworthy applicants than capital. Deciding *which* subset to fund under a
fixed budget is a 0-1 knapsack — NP-hard, natively binary, and exactly the shape of problem
QAOA was built for."

**0:20 — Show the architecture slide.** Point at the arrow from the classifier to the
Hamiltonian. Say the word **series**:
"Most hybrid projects run the AI and the quantum part in parallel — a classifier, then a quantum
classifier doing the same job. Ours run in series. The model's calibrated default probabilities
*are* the coefficients of the cost Hamiltonian. Remove the AI and there's no optimisation
problem left."

**0:50 — Live: move the budget slider.** Watch the funded portfolio change. Say the qubit count
out loud as it updates (10→14→16).

**1:30 — Live: toggle the fairness penalty.** This is the money shot. Approval-rate gap goes
from 0.28 to 0.03; profit drops about 4%.
"We didn't write a fairness paragraph. We put parity in the objective as a squared penalty —
which costs zero extra qubits and is what makes this Hamiltonian genuinely quadratic. And we
can tell you the price of parity in money."

**2:10 — Open the Cost Hamiltonian tab.** Point at one ZZ term.
"That coupling is two specific applicants competing for the same capital."

**2:30 — The comparison page.** Lead with the loss, don't hide it:
"QAOA is a few hundred times slower than exhaustive search at this size and we're not claiming
otherwise. But against the greedy heuristic a bank would actually deploy, QAOA wins on
approximation ratio and on how often it finds the true optimum."

Then the methodological point, which is the one that separates you:
"We also can't tell you which circuit depth is best — and we can show you why. The variance
across optimiser seeds is as large as the difference between depths. Our first benchmark said
p=2 was clearly best; re-running it said p=2 was clearly worst. So we report 3 seeds per cell
instead of 1."

**2:50 — Close on the scaling wall.**
"We measured where this stops working: 16 qubits is fine, 30 is 17 GB, 68 is impossible. That's
why we scoped it here."

---

## Questions a quantum-literate judge will ask

**"Why quantum? Isn't this just a knapsack you could solve exactly in 20 ms?"**
Yes, at n=10. We're not claiming advantage at this scale — the brief says small qubit counts,
simulator only, and we stayed inside it deliberately. What we're demonstrating is a correct
end-to-end mapping and an honest measurement of where it breaks. The crossover for QAOA on
combinatorial problems is hundreds of qubits (Guerreschi & Matsuura, Sci. Rep. 9:6903, 2019).

**"Your objective is linear. Where's the quadratic structure?"**
Two places. The budget inequality becomes a squared penalty under `QuadraticProgramToQubo`, and
the fairness parity term is a squared linear form. Without fairness this is a linear objective
wearing a QUBO costume; with it, applicants of opposite groups genuinely couple. That was a
design decision, not an accident.

**"How many qubits, and why that many?"**
14 for the default instance: 10 decision variables plus 4 binary slack bits. The slack comes
from the budget being an *inequality* — `ceil(log2(budget+1))`. Discretising capital into coarse
units is the lever that controls qubit count, and it's the single most important modelling
choice in the project.

**"Did you compare against a real classical solver or a strawman?"**
Exhaustive enumeration — the true optimum, not an approximation. Plus the greedy
value-per-capital heuristic. Both on the same QUBO, same instances. Our classical baseline is
the strongest one available at this size.

**"Your quantum result is worse than classical. Isn't that a failed project?"**
It's the correct result, reported over 8 instances with spread rather than one lucky run. We'd
argue a fabricated quantum win is the failure mode here — it doesn't survive the question you
just asked.

**"Which QAOA depth is best?"**
We can't tell you, and that's our most interesting result. We ran this with one QAOA seed per
cell first and got a clean ranking with p=2 on top. Re-running with different transpilation
put p=2 *last*. Same code, same instances. So we re-ran with 3 QAOA seeds per (instance, depth)
and measured it properly: the spread within a single cell is as large as the spread between
depths. At this scale the depth ranking is optimiser-seed luck. Anyone showing you a
single-seed table with a "best depth" is reporting noise — we nearly did.

**"Would this work on real hardware?"**
We swept a depolarizing two-qubit gate error and the honest answer is: our sweep cannot tell
you. Scatter within one error level across seeds is 0.1365; the spread between error levels is
0.0268. The trend is several times smaller than its own noise floor, so we do not draw a
degradation curve. Resolving it would take ~104 seeds per level, about 8 hours of noisy
simulation.

The interesting part is what that cost us. We first ran 3 seeds, which estimated only ~8 seeds
would settle it. At 12 seeds the measured scatter came out ~2.5x larger than the pilot thought,
and the requirement jumped to ~104. The pilot had underestimated its own error bars -- a small
sample is unreliable about effects AND about how much data you would need. We also retracted a
claim from that pilot: at 3 seeds best-of-N readout returned the exact optimum at every error
level, which looked like clean evidence that the default statistic is noise-blind. At 12 seeds
it ranges 0.9188 to 1.0000 and the claim does not hold. We removed it.

**"Why should I trust this dataset?"**
It is 30,000 real Taiwanese credit-card accounts from 2005 with a real 22.1% default rate. We
started on German Credit, the usual benchmark, and moved off it: 1,000 rows from 1973-75, a
default rate that is a stratified over-sample rather than a real rate, and — decisively — sex is
not recoverable from it. Groemping (2019) showed male singles and female non-singles share code
A92, and A95 has zero rows in the published file, so any "female" group is a mixed bag. Most
published fairness work on that dataset uses exactly that variable.

**"Is your AI model any good?"**
AUC 0.780 for the calibrated gradient-boosted model against 0.715 for tuned logistic regression,
on 21,000 training rows. On the 1,000-row German Credit data we started from that ordering was
reversed — boosting needs data to beat a well-specified linear model, and that is part of why we
moved datasets. Calibration matters more than discrimination here, because the optimiser
multiplies these probabilities by cash amounts: Brier is the number to read (0.135).

---

## Things to *not* say

- Don't say "quantum speedup." You don't have one and the numbers are on your own page.
- Don't say the model is "fair." Say you can *price* parity: the approval-rate gap closes from
  0.28 to 0.03 for about 4% of profit.
- Don't quote absolute profit as if it were a real P&L. It is one 10-account slice of a 2005
  Taiwanese card book.
