/** The optimisation problem, mirroring src/portfolio.py exactly.
 *
 *   maximise   Σ EVᵢ·xᵢ − γ·concentration(x) − λ·parityGap(x)²
 *   subject to Σ unitsᵢ·xᵢ ≤ budget
 *
 * The browser solves this EXACTLY by enumerating all 2ⁿ portfolios (instant at n ≤ 12). That is
 * the ground-truth solver from the benchmark. QAOA — the quantum approximate solver — runs in the
 * project's Python backend and is measured against this exact answer there. */
import { APPLICANTS, type Applicant } from "../data/applicants";
import { mulberry32 } from "./rng";

export type Bits = number[];
export interface Problem { pool: Applicant[]; budget: number; n: number; qubits: number; }
export interface SpecEntry { e: number; feasible: boolean; mask: number; }
export interface Solution { x: Bits; obj: number; }
export interface ExactResult extends Solution { spectrum: SpecEntry[]; }

export const UNIT_NT = 20000;

export function samplePool(n: number, seed: number, budgetFrac: number): Problem {
  const rng = mulberry32(1000 + seed * 97);
  const idx = APPLICANTS.map((_, i) => i);
  for (let i = idx.length - 1; i > 0; i--) { const j = Math.floor(rng() * (i + 1)); [idx[i], idx[j]] = [idx[j], idx[i]]; }
  const pool = idx.slice(0, n).map(i => APPLICANTS[i]);
  const total = pool.reduce((a, p) => a + p.units, 0);
  const budget = Math.max(2, Math.round(budgetFrac * total));
  // n decision qubits + binary slack for the budget inequality (QuadraticProgramToQubo)
  const qubits = n + Math.ceil(Math.log2(budget + 1));
  return { pool, budget, n, qubits };
}

/** Sorted labels → "female" < "male": the first group is the protected mask (group_mask in Python). */
const isFirst = (p: Applicant) => p.group === "female";

export function used(P: Problem, x: Bits) { return P.pool.reduce((a, p, i) => a + p.units * x[i], 0); }
export function profit(P: Problem, x: Bits) { return P.pool.reduce((a, p, i) => a + p.ev * x[i], 0); }
export function feasible(P: Problem, x: Bits) { return used(P, x) <= P.budget; }

/** Herfindahl concentration of capital across segments: Σₛ (Σᵢ∈ₛ wᵢxᵢ)², wᵢ = unitsᵢ / budget. */
export function concentration(P: Problem, x: Bits) {
  const by: Record<string, number> = {};
  P.pool.forEach((p, i) => { by[p.sector] = (by[p.sector] ?? 0) + (p.units / Math.max(P.budget, 1)) * x[i]; });
  return Object.values(by).reduce((a, v) => a + v * v, 0);
}
/** Approval-rate gap between the two groups. */
export function parityGap(P: Problem, x: Bits) {
  let f = 0, nf = 0, m = 0, nm = 0;
  P.pool.forEach((p, i) => { if (isFirst(p)) { nf++; f += x[i]; } else { nm++; m += x[i]; } });
  return f / Math.max(nf, 1) - m / Math.max(nm, 1);
}
export function objective(P: Problem, x: Bits, gamma: number, lambda: number) {
  return profit(P, x) - gamma * concentration(P, x) - lambda * parityGap(P, x) ** 2;
}

/** Exact optimum by enumeration, plus the full energy spectrum for the landscape view. */
export function solveExact(P: Problem, gamma: number, lambda: number): ExactResult {
  const n = P.n, N = 1 << n;
  const penalty = 3 * P.pool.reduce((a, p) => a + Math.abs(p.ev), 0) + 1;
  const spectrum: SpecEntry[] = new Array(N);
  const x: Bits = new Array(n).fill(0);
  let bx: Bits = new Array(n).fill(0), bv = -Infinity;
  for (let m = 0; m < N; m++) {
    for (let i = 0; i < n; i++) x[i] = (m >> i) & 1;
    const over = Math.max(0, used(P, x) - P.budget);
    const obj = objective(P, x, gamma, lambda);
    spectrum[m] = { e: -obj + penalty * over * over, feasible: over === 0, mask: m };
    if (over === 0 && obj > bv) { bv = obj; bx = x.slice(); }
  }
  spectrum.sort((a, b) => a.e - b.e);
  return { x: bx, obj: bv, spectrum };
}

/** Greedy value-per-capital heuristic — the classical baseline a bank would actually deploy. */
export function solveGreedy(P: Problem, gamma: number, lambda: number): Solution {
  const order = P.pool.map((_, i) => i).sort((a, b) => P.pool[b].ev / P.pool[b].units - P.pool[a].ev / P.pool[a].units);
  const x: Bits = new Array(P.n).fill(0); let u = 0;
  for (const i of order) { if (P.pool[i].ev <= 0) continue; if (u + P.pool[i].units <= P.budget) { x[i] = 1; u += P.pool[i].units; } }
  return { x, obj: objective(P, x, gamma, lambda) };
}

export function maskOf(x: Bits) { return x.reduce((m, v, i) => (v ? m | (1 << i) : m), 0); }
