# Research paper plan

**Working title:** *Under-powered by construction: seed variance and unreliable power
estimates in small-scale QAOA benchmarking*

**Author:** Tanishq Aryan · **Status:** plan, not yet drafted · **Created:** 10 Sep 2026

> The paper is **not** about loans. The portfolio problem is the testbed and gets one page.
> The contribution is a measurement result about how the field benchmarks QAOA.

---

## 1. Thesis

Two claims, the second of which is the novel one.

1. **At simulable qubit counts, QAOA's run-to-run variance exceeds the effect sizes routinely
   reported as findings.** Depth rankings, aggregation-strategy comparisons and noise-degradation
   curves are frequently measurements of optimiser-seed luck.

2. **The standard remedy fails in the same direction.** A pilot study used to size the
   experiment systematically *underestimates its own variance*, so a researcher who does the
   responsible thing still arrives at an under-powered design, and at unwarranted confidence.

Claim 1 is a sharper version of something people half-suspect. Claim 2 is, as far as the
literature audit will establish, unreported.

---

## 2. Evidence already in hand

Every number below is measured and lives in `artifacts/`. This is the paper's spine.

| Comparison | Between-condition spread | Within-cell noise floor | Ratio |
| --- | --- | --- | --- |
| QAOA depth p in {1,2,3} | 0.0036 | 0.0211 | **5.9x too small** |
| CVaR vs mean aggregation | 0.0060 | 0.0258 | **4.3x too small** |
| Depolarizing gate-error sweep | 0.0268 | 0.1365 | **5.1x too small** |

Supporting facts:

- **The depth ranking reversed.** A single-seed run ranked p=2 clearly best; re-running
  identical code with different transpilation ranked p=2 clearly *worst*.
- **The pilot underestimation.** A 3-seed pilot estimated 8 seeds per level would resolve the
  noise sweep. At 12 seeds the measured within-level scatter was about 2.5x larger and the
  requirement had moved to **104 seeds** (~7.7 h). A 13x miss.
- **A retracted claim.** On 3-seed data, best-of-2048-shots readout returned the optimum at
  every error level, which read as evidence the statistic is noise-blind. At 12 seeds it ranges
  0.9188 to 1.0000. Withdrawn.

---

## 3. Draft abstract

> Variational quantum algorithms are routinely benchmarked at qubit counts small enough to
> simulate, and comparisons between circuit depths, aggregation strategies and noise levels are
> reported as findings. We show that at these scales such comparisons are frequently dominated
> by optimiser-seed variance rather than by the effect under study. Using a 14-qubit constrained
> portfolio-selection QUBO as a testbed, we measure the within-cell scatter of QAOA's
> approximation ratio across repeated runs of identical configurations and compare it to the
> spread between the conditions being contrasted. Across three standard comparisons, circuit
> depth p in {1,2,3}, CVaR versus mean aggregation, and a depolarizing gate-error sweep, the
> between-condition spread is 4 to 6 times smaller than the within-cell noise floor. In each
> case a single-seed protocol produced a confident and irreproducible conclusion; re-running
> identical code with different transpilation reversed the depth ranking.
>
> We further show that the standard remedy fails in the same direction. A three-seed pilot
> estimated that eight seeds per condition would resolve the noise sweep; at twelve seeds the
> measured variance was 2.5x larger and the requirement had moved to 104. The pilot did not
> merely fail to detect the effect, it underestimated its own error bars. We characterise this
> underestimation as a function of pilot size, audit N recent QAOA benchmarking papers for
> variance reporting, and propose a minimal protocol: report within-cell scatter alongside every
> between-condition difference, and claim nothing whose difference is smaller than its own
> noise floor.

---

## 4. Section outline

| Sec | Section | Content | Status |
| --- | --- | --- | --- |
| 1 | Introduction | The three claim types that recur in QAOA papers. Preview the reversal. | write |
| 2 | Related work and audit | Survey of variance reporting in recent QAOA benchmarking. | **E4 needed** |
| 3 | Testbed | The portfolio QUBO, penalties, slack qubits. **One page, no more.** | reuse REPORT.pdf §4 |
| 4 | Protocol | Within-cell vs between-condition estimator; how cells are seeded. | write |
| 5.1 | Depth ranking is noise | The 0.0036 / 0.0211 result plus the reversal. | **have** |
| 5.2 | Aggregation inside the floor | CVaR +0.0138 vs 0.0258 scatter. | **have** |
| 5.3 | Noise sweep inconclusive | 0.0268 / 0.1365; 104 seeds needed. | **have** |
| 5.4 | **Pilot underestimation** | Seed-requirement estimate vs pilot size. **Headline figure.** | **E1 needed** |
| 6 | Generality | Replication on other problem classes. | **E2 needed** |
| 7 | Recommendations | The minimal reporting protocol. | write |
| 8 | Threats to validity | One optimiser (COBYLA), one simulator, one ansatz family. | write |
| 9 | Conclusion | | write |

---

## 5. Experiments still to run

Priority order. Compute is hours, not days.

### E1 — The pilot-underestimation curve  (the paper's headline)

Run pilots at k = 3, 5, 8, 12, 20, 40 seeds. For each k, compute the implied
"seeds needed to resolve" estimate. Plot estimate vs k with bootstrap confidence intervals.
If it climbs monotonically and stabilises only late, the trap is quantified.
*Nobody has this figure.* Extends `src/noise_ablation.py`. **~10 h compute.**

### E2 — Generality across problem classes

Replicate the §5.1 variance analysis on **MaxCut** (the field standard) and one other
(max independent set, or number partitioning). With one problem class a reviewer says n=1
and they are right. **~6 h compute, ~2 days of code.**

### E3 — Complete the noise sweep

104 seeds x 5 error levels is about **8 h**. Either it resolves into a real degradation curve,
or the inconclusiveness becomes a *measured* result instead of an admission. Just run it.

### E4 — Literature audit

30 to 50 recent QAOA benchmarking papers. Coding sheet per paper:

- [ ] Number of seeds / repeats per configuration reported?
- [ ] Any dispersion statistic (std, CI, IQR) on the headline metric?
- [ ] Is a "best" depth or setting named?
- [ ] If named, is the margin larger than any reported dispersion?
- [ ] Is the transpilation seed fixed or reported?

If most papers name a winner without reporting dispersion, that table *is* §2 and it is the
paper's motivation. **Zero compute, 1 to 2 weeks reading. Highest leverage per hour.**

---

## 6. Venue and sequencing

1. **arXiv (quant-ph) preprint** first. Immediate, free, citable, establishes priority.
2. **IEEE QCE / Quantum Week**, about 8 pages. Receptive to empirical and reproducibility work.
3. *Quantum* (journal) is a stretch but plausible if E1 and E2 land solidly.

Release the harness with the paper. Multi-seed benchmarking with noise-floor reporting is
itself a contribution, since most published setups do not do it.

---

## 7. Timeline (part-time)

| Weeks | Work |
| --- | --- |
| 1-2 | E4 literature audit; draft §1-2 |
| 3 | E3 noise sweep; build E1 harness |
| 4-5 | E1 runs and headline figure; draft §4-5 |
| 6-7 | E2 replication; draft §6-8 |
| 8 | Full draft, internal review, arXiv |

---

## 8. Risks

- **"This is just statistics 101."** Rebuttal: claim 2, and the audit showing the field does not
  do it. Lead with the reversal, not with the definition of variance.
- **Reviewers whose papers the audit implicates.** Anonymise the audit. Report counts and
  distributions, never a name-and-shame table.
- **Single optimiser.** COBYLA is one choice. Either add SPSA as a robustness check, or scope
  the claim explicitly in §8.
- **Scope creep back into the loan application.** §3 stays at one page. If it grows, cut it.

---

## 9. Get an advisor

Find a co-author with quant-ph publishing experience. This argument will attract pushback, and
framing plus reviewer response is much easier with someone who has been through it.
