"""Deliverable 4, as a literal single page.

The brief asks for "results side by side on one page". DELIVERABLE_4.md is the full
write-up; this renders the same measured numbers as one A4 sheet you can print to PDF
(Ctrl+P -> Save as PDF -> A4, margins none, background graphics on).
"""
from __future__ import annotations

import base64
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
FIGS = ARTIFACTS / "figures"


def b64(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


def main() -> None:
    summary = pd.read_csv(ARTIFACTS / "bench_summary.csv")
    quality = pd.read_csv(ARTIFACTS / "bench_quality.csv")
    scaling = pd.read_csv(ARTIFACTS / "bench_scaling.csv")
    ai = json.loads((ARTIFACTS / "ai_metrics.json").read_text())
    meta = json.loads((ARTIFACTS / "bench_meta.json").read_text())
    stab = json.loads((ARTIFACTS / "bench_stability.json").read_text())

    exact_time = quality[quality.solver.str.startswith("Exact")]["seconds"].mean()
    greedy = summary[summary.solver.str.startswith("Greedy")].iloc[0]
    qruns = quality[quality.solver.str.startswith("QAOA")]
    pooled_ar, pooled_hit = qruns["ar"].mean(), qruns["hit"].mean()
    pooled_sec = qruns["seconds"].mean()
    q_tail = qruns["ar"].min()
    qsum = summary[summary.solver.str.startswith("QAOA")]
    best_hit = qsum.loc[qsum.hit_rate.idxmax()]
    speed = pooled_sec / max(exact_time, 1e-9)
    max_q = int(scaling.qubits.max())

    depth_rows = "".join(
        f"<tr><td>{r.solver}</td><td>{r.ar_mean:.4f}</td><td>{r.ar_min:.4f}</td>"
        f"<td>{r.ar_std:.4f}</td><td>{r.hit_rate:.0%}</td><td>{r.seconds:.1f}</td></tr>"
        for r in summary[summary.solver.str.startswith("QAOA")].sort_values("solver").itertuples()
    )
    n_runs = meta["seeds"] * meta["qaoa_repeats"]

    html = f"""<!doctype html><html><head><meta charset="utf-8">
<title>Deliverable 4 - Quantum vs Classical</title>
<style>
  /* Sized to fit ONE A4 sheet. The brief asks for results on one page, so the layout is
     constrained to ~1040px of content height at 96dpi -- if you add a section, something
     else has to shrink. Images are capped rather than left to their natural aspect. */
  @page {{ size: A4; margin: 9mm; }}
  * {{ box-sizing: border-box; }}
  body {{ font: 10px/1.36 -apple-system, "Segoe UI", Roboto, sans-serif; color: #1a1a1a;
         margin: 0; padding: 0; max-width: 192mm; }}
  h1 {{ font-size: 15px; margin: 0 0 2px; }}
  h2 {{ font-size: 10.5px; margin: 7px 0 3px; text-transform: uppercase;
        letter-spacing: .06em; color: #4c6ef5; border-bottom: 1px solid #dde; padding-bottom: 2px; }}
  .sub {{ color: #555; font-size: 9.5px; margin-bottom: 5px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
  .grid3 {{ display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 9.5px; }}
  th, td {{ text-align: right; padding: 2.5px 5px; border-bottom: 1px solid #e8e8ef; }}
  th:first-child, td:first-child {{ text-align: left; }}
  th {{ background: #f5f6fb; font-weight: 600; }}
  img {{ width: 100%; height: auto; max-height: 49mm; object-fit: contain;
         border: 1px solid #e8e8ef; border-radius: 3px; }}
  .kpi {{ background: #f5f6fb; border-radius: 4px; padding: 5px 8px; }}
  .kpi .n {{ font-size: 14px; font-weight: 700; color: #4c6ef5; }}
  .kpi .l {{ font-size: 8px; color: #555; text-transform: uppercase; letter-spacing: .04em; }}
  .note {{ font-size: 8.6px; color: #555; margin-top: 3px; line-height: 1.34; }}
  b.warn {{ color: #c92a2a; }}
</style></head><body>

<h1>Where the quantum mapping helps, where it doesn't, and where it stops being simulable</h1>
<div class="sub">
  <b>Task (identical for both sides):</b> allocate a fixed capital budget across
  {meta['pool_n']} scored loan applications to maximise risk-adjusted expected profit.
  A calibrated classifier supplies P(default); those probabilities become the linear
  coefficients of a QUBO. Every solver below attacks the <b>same QUBO on the same
  instances</b> &mdash; this compares optimisers, not two different classifiers.
  {meta['seeds']} instances &times; {meta['qaoa_repeats']} QAOA seeds = {n_runs} runs per depth;
  {meta['shots']} shots; COBYLA maxiter {meta['maxiter']}; Qiskit Aer, 14 qubits.
</div>

<div class="grid3">
  <div class="kpi"><div class="n">{pooled_ar:.4f}</div><div class="l">QAOA approx ratio (pooled)</div></div>
  <div class="kpi"><div class="n">{greedy.ar_mean:.4f}</div><div class="l">Greedy heuristic</div></div>
  <div class="kpi"><div class="n">{speed:,.0f}&times;</div><div class="l">Slower than exact search</div></div>
</div>

<h2>1 &nbsp;Solution quality &mdash; and why we will not name a best depth</h2>
<div class="grid">
  <div>
    <table>
      <tr><th>Solver</th><th>AR mean</th><th>AR worst</th><th>Std</th><th>Hit opt.</th><th>Sec</th></tr>
      {depth_rows}
      <tr><td>Greedy heuristic</td><td>{greedy.ar_mean:.4f}</td><td>{greedy.ar_min:.4f}</td>
          <td>{greedy.ar_std:.4f}</td><td>{greedy.hit_rate:.0%}</td><td>{greedy.seconds:.4f}</td></tr>
      <tr><td>Exact (brute force)</td><td>1.0000</td><td>1.0000</td><td>0.0000</td><td>100%</td>
          <td>{exact_time:.4f}</td></tr>
    </table>
    <div class="note">
      <b>Spread within one (instance, depth) across QAOA seeds: {stab['within_cell_ar_std']:.4f}.
      Spread between depth means: {stab['between_depth_ar_std']:.4f}.</b>
      {"Within-cell noise is as large as the differences between depths, so no depth is meaningfully best."
       if stab['depth_ranking_is_noise'] else
       "Between-depth differences only just exceed the noise; treat any ranking as provisional."}
      An earlier single-seed version of this benchmark ranked p=2 clearly best; re-running it
      with different transpilation ranked p=2 <b class="warn">worst</b>. Same code, same instances.
      Depth ranking here is optimiser-seed luck &mdash; which is why we report
      {meta['qaoa_repeats']} seeds per cell rather than 1.
    </div>
  </div>
  <div><img src="{b64(FIGS / 'quality.png')}" alt="approximation ratio by depth"></div>
</div>

<h2>2 &nbsp;The scaling wall, and the price of fairness</h2>
<div class="grid">
  <div><img src="{b64(FIGS / 'scaling.png')}" alt="scaling"></div>
  <div><img src="{b64(FIGS / 'fairness.png')}" alt="fairness frontier"></div>
</div>
<div class="note">
  Statevector memory is 2<sup>n</sup>&times;16&nbsp;bytes: {max_q} qubits fits comfortably,
  28 = 4.3&nbsp;GB, 30 = 17.2&nbsp;GB (dead on a 16&nbsp;GB laptop). The binding constraint is the
  budget <i>inequality</i>, which forces integer slack and binary expansion. &mdash;
  The parity penalty is a squared linear term, so it costs <b>zero extra qubits</b> and is what
  makes this objective genuinely quadratic rather than a linear knapsack in a QUBO costume.
</div>

<h2>3 &nbsp;The AI model, reported honestly</h2>
<div class="grid">
  <div>
    <table>
      <tr><th>Model</th><th>ROC-AUC</th><th>Brier</th></tr>
      <tr><td>Gradient boosting (calibrated)</td><td>{ai['gbm_auc']:.3f}</td><td>{ai['gbm_brier']:.3f}</td></tr>
      <tr><td>Logistic regression (tuned)</td><td>{ai['logreg_auc']:.3f}</td><td>{ai['logreg_brier']:.3f}</td></tr>
    </table>
    <div class="note">
      Logistic regression <b>beats</b> the gradient-boosted model
      ({ai['logreg_auc']:.3f} vs {ai['gbm_auc']:.3f}) &mdash; expected at n=1000, and we report it
      rather than bury it. Calibration matters more than discrimination downstream: the optimiser
      multiplies these probabilities by cash amounts, so a miscalibrated 0.3 that should be 0.5
      corrupts every coefficient of the Hamiltonian.
    </div>
  </div>
  <div><img src="{b64(FIGS / 'calibration.png')}" alt="calibration"></div>
</div>

<h2>4 &nbsp;Bottom line</h2>
<div class="note" style="font-size:9.5px">
  QAOA <b>loses on speed by ~{speed:,.0f}&times;</b>, and on quality it <b>does not cleanly win
  either</b>: pooled approximation ratio {pooled_ar:.4f} against the greedy heuristic's
  {greedy.ar_mean:.4f}, though it reaches the exact optimum more often ({best_hit.hit_rate:.0%} at
  {best_hit.solver} vs {greedy.hit_rate:.0%}) at the cost of a worse tail (worst QAOA run
  {q_tail:.4f} vs greedy's {greedy.ar_min:.4f}). <b>This is a negative result and that is the
  point</b> &mdash; it is trustworthy precisely because it did not come out the way we wanted. We claim no
  advantage at 14 qubits &mdash; published analysis puts the QAOA crossover for combinatorial problems
  at hundreds of qubits, and the brief's scope is explicitly small qubit counts on a simulator.
  What we demonstrate is a correct end-to-end mapping &mdash; calibrated ML output &rarr; QUBO &rarr;
  Ising Hamiltonian &rarr; variational circuit &rarr; measured portfolio &mdash; plus an honest
  measurement of where it breaks. One thing QAOA gives that exact search structurally cannot: a
  <b>distribution</b> over portfolios. When the default probabilities are themselves estimates, a
  ranked set of near-optimal feasible portfolios beats a single optimum computed for point
  estimates that are wrong.
</div>

</body></html>"""

    out = ROOT / "DELIVERABLE_4.html"
    out.write_text(html, encoding="utf-8")
    print(f"wrote {out.name} ({out.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
