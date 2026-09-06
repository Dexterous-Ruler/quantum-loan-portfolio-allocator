import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { samplePool, solveExact, solveGreedy, maskOf, profit, withBudget, type Bits } from "./lib/problem";
import { Scene } from "./scene/Scene";
import { Controls, Readouts, Num, type ControlsState } from "./ui/Panels";
import { Landscape } from "./ui/Landscape";
import { ProfitCurve, type CurvePt } from "./ui/ProfitCurve";

const REDUCED = typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const BUDGET_FRACS = [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9];

export default function App() {
  const [s, setS] = useState<ControlsState>({ n: 10, budgetFrac: 0.45, gOn: false, gamma: 40000, lOn: false, lambda: 200000, seed: 0, mode: "opt" });
  const set = useCallback((patch: Partial<ControlsState>) => setS(prev => ({ ...prev, ...patch })), []);
  const [manual, setManual] = useState<Bits>([]);
  const [solveTick, setTick] = useState(0);
  const [flash, setFlash] = useState(false);

  const gamma = s.gOn ? s.gamma : 0, lambda = s.lOn ? s.lambda : 0;
  const P = useMemo(() => samplePool(s.n, s.seed, s.budgetFrac), [s.n, s.seed, s.budgetFrac]);
  const best = useMemo(() => solveExact(P, gamma, lambda), [P, gamma, lambda]);
  const greedy = useMemo(() => solveGreedy(P, gamma, lambda), [P, gamma, lambda]);
  const unconstrained = useMemo(() => (gamma || lambda) ? solveExact(P, 0, 0) : null, [P, gamma, lambda]);
  // Profit at every budget level for the same pool — solved exactly, keyed on the pool not the budget.
  const curve = useMemo<CurvePt[]>(() => {
    const seen = new Map<number, CurvePt>();
    for (const f of BUDGET_FRACS) { const Pf = withBudget(P, f); if (seen.has(Pf.budget)) continue; seen.set(Pf.budget, { frac: f, budget: Pf.budget, profit: profit(Pf, solveExact(Pf, gamma, lambda).x) }); }
    return [...seen.values()].sort((a, b) => a.budget - b.budget);
  }, [P.pool, gamma, lambda]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { setManual(new Array(P.n).fill(0)); }, [P]);
  useEffect(() => { if (s.mode !== "opt") return; setTick(t => t + 1); setFlash(true); const id = setTimeout(() => setFlash(false), 1500); return () => clearTimeout(id); }, [best, s.mode]);

  const man = s.mode === "man" ? manual : null;
  const shown = man ?? best.x;
  const onPick = useCallback((i: number) => setManual(m => { const c = m.slice(); c[i] = c[i] ? 0 : 1; return c; }), []);
  const ratio = greedy.obj / Math.max(best.obj, 1e-9);

  return (
    <div className="page">
      <motion.header className="top" initial={{ y: -16, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.5 }}>
        <div className="brand">
          <h1>Quantum Loan Book</h1>
          <p>Which borrowers should a bank fund when it can't fund them all? AI prices the risk; the optimiser finds the ground state.</p>
        </div>
        <div className="kpis">
          <div className="kpi"><div className="l">Customers</div><div className="v">{P.n}</div></div>
          <div className="kpi"><div className="l">Budget</div><div className="v">{P.budget} units</div></div>
          <div className="kpi teal"><div className="l">Qubits</div><div className="v">{P.qubits}</div></div>
          <div className="kpi gold"><div className="l">Optimal profit</div><div className="v"><Num value={profit(P, best.x)} prefix="NT$ " /></div></div>
        </div>
      </motion.header>

      {/* ---------- 1. the floor ---------- */}
      <section className="floor">
        <Controls s={s} set={set} onReset={() => setManual(new Array(P.n).fill(0))} />
        <main className="stage">
          <Scene P={P} x={best.x} manual={man} gOn={s.gOn} lOn={s.lOn} solveTick={solveTick} onPick={onPick} reduced={REDUCED} />
          <AnimatePresence>{flash && s.mode === "opt" && (
            <motion.div className="flash" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>Ground state found</motion.div>
          )}</AnimatePresence>
          <div className="hint">{s.mode === "man" ? "Click people to fund them · stay under budget · try to reach the ground state" : "Drag to look around · scroll to zoom · hover a person for their numbers"}</div>
        </main>
        <Readouts P={P} best={best} greedy={greedy} unconstrained={unconstrained} shown={shown} manual={man} gamma={gamma} lambda={lambda} gOn={s.gOn} lOn={s.lOn} />
      </section>

      {/* ---------- 2. the charts ---------- */}
      <section>
        <div className="section-head"><h2>The numbers behind the floor</h2><span>both charts solved exactly · updated live</span></div>
        <div className="charts">
          <div className="card">
            <h2>Profit across every budget</h2>
            <ProfitCurve pts={curve} current={P.budget} />
            <div className="stat"><span>Greedy heuristic vs. the optimum</span><b>{(ratio * 100).toFixed(1)}%</b></div>
          </div>
          <div className="card">
            <div className="section-head"><h2>Energy landscape — every possible portfolio</h2><span>ground state marked · lower is better</span></div>
            <Landscape spectrum={best.spectrum} currentMask={man ? maskOf(man) : null} n={P.n} qubits={P.qubits} />
            <div className="cap"><span>each bar is one of the 2ⁿ ways to fund the pool</span><span>grey band = over budget</span></div>
          </div>
        </div>
      </section>

      {/* ---------- 3. how to read it ---------- */}
      <section>
        <div className="section-head"><h2>How to read this</h2></div>
        <div className="explain">
          <div className="card">
            <h2>What you're looking at</h2>
            <p>Each person on the floor is a <b>real credit-card customer</b> from a 30,000-account dataset. An AI model has already read their payment history and priced their risk — hover anyone to see their default probability and expected value.</p>
            <p>The bank can't fund everyone. The optimiser picks the group that earns the most <b>within the capital budget</b>. Funded people step onto the lit stage and raise their arms; the rest stand back. Coin stacks show how much capital each one needs; the floor ring shows their risk.</p>
          </div>
          <div className="card">
            <h2>The two modes</h2>
            <ul>
              <li><b>Optimiser</b> — the solver chooses automatically. Change the pool, the budget, or the rules on the left and watch it re-solve in real time. This is the machine doing the work.</li>
              <li><b>You vs optimiser</b> — <em>you</em> choose. Click people on the floor to fund them, stay under budget, and try to match the optimiser's profit. It's a game that lets you feel how hard the problem is — the number of possible combinations doubles with every customer.</li>
            </ul>
          </div>
          <div className="card">
            <h2>Honest note</h2>
            <p>The <span className="q">energy landscape</span> is the real spectrum of the problem's <span className="q">Ising Hamiltonian</span>: every configuration scored and sorted. The gold point is the <b>ground state</b>, the lowest-energy configuration — and by construction it <i>is</i> the optimal book.</p>
            <p>This page finds it with the <b>exact</b> ground-truth solver, enumerating all 2ⁿ portfolios (instant at n ≤ 12). <span className="q">QAOA</span>, the quantum approximate solver, runs in the project's Python backend and is benchmarked against this exact answer there.</p>
          </div>
        </div>
      </section>
    </div>
  );
}
