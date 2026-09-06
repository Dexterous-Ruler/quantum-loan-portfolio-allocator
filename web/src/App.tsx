import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { samplePool, solveExact, solveGreedy, maskOf, profit, withBudget, UNIT_NT, type Bits } from "./lib/problem";
import { Scene } from "./scene/Scene";
import { Controls, Readouts, Legend, Num, type ControlsState } from "./ui/Panels";
import { Landscape } from "./ui/Landscape";
import { ProfitCurve, type CurvePt } from "./ui/ProfitCurve";
import { HelpDrawer } from "./ui/HelpDrawer";

const REDUCED = typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;
const BUDGET_FRACS = [0.2, 0.25, 0.3, 0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8, 0.85, 0.9];

export default function App() {
  const [s, setS] = useState<ControlsState>({ n: 10, budgetFrac: 0.45, gOn: false, gamma: 40000, lOn: false, lambda: 200000, seed: 0, mode: "opt" });
  const set = useCallback((patch: Partial<ControlsState>) => setS(prev => ({ ...prev, ...patch })), []);
  const [manual, setManual] = useState<Bits>([]);
  const [solveTick, setTick] = useState(0);
  const [flash, setFlash] = useState(false);
  const [help, setHelp] = useState(false);
  const closeHelp = useCallback(() => setHelp(false), []);

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
    <div className="app">
      <motion.header className="topbar" initial={{ y: -12, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.45 }}>
        <div className="brand">
          <h1>Quantum Loan Book</h1>
          <p>AI prices the risk · the optimiser finds the ground state</p>
        </div>
        <div className="kpis">
          <div className="kpi"><div className="l">Customers</div><div className="v">{P.n}</div></div>
          <div className="kpi"><div className="l">Budget</div><div className="v">NT$ <Num value={P.budget * UNIT_NT} /></div></div>
          <div className="kpi teal"><div className="l">Qubits</div><div className="v">{P.qubits}</div></div>
          <div className="kpi gold"><div className="l">Optimal profit</div><div className="v"><Num value={profit(P, best.x)} prefix="NT$ " /></div></div>
        </div>
        <button className="help-btn" onClick={() => setHelp(true)} aria-haspopup="dialog"><span>?</span>How to read this</button>
      </motion.header>

      <div className="body">
        <Controls s={s} set={set} onReset={() => setManual(new Array(P.n).fill(0))} P={P} />

        <main className="stage">
          <Scene P={P} x={best.x} manual={man} gOn={s.gOn} lOn={s.lOn} solveTick={solveTick} onPick={onPick} reduced={REDUCED} />
          <AnimatePresence>{flash && s.mode === "opt" && (
            <motion.div className="flash" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>Ground state found</motion.div>
          )}</AnimatePresence>
          <div className="hint">{s.mode === "man" ? "Click people to fund them · stay under budget · reach the ground state" : "Drag to look around · scroll to zoom · hover a person for their numbers"}</div>
          <Legend />
        </main>

        <div className="charts">
          <div className="card chart-card">
            <div className="chart-head"><h2>Profit across every budget</h2><span>solved exactly at each budget</span></div>
            <ProfitCurve pts={curve} current={P.budget} />
            <div className="chart-foot"><span>greedy heuristic vs. the optimum</span><b>{(ratio * 100).toFixed(1)}%</b></div>
          </div>
          <div className="card chart-card">
            <div className="chart-head"><h2>Energy landscape — every possible portfolio</h2><span>ground state marked · lower is better</span></div>
            <Landscape spectrum={best.spectrum} currentMask={man ? maskOf(man) : null} n={P.n} qubits={P.qubits} />
            <div className="chart-foot"><span>each point is one of the 2ⁿ ways to fund the pool</span><span>grey band = over budget</span></div>
          </div>
        </div>

        <Readouts P={P} best={best} greedy={greedy} unconstrained={unconstrained} shown={shown} manual={man} gamma={gamma} lambda={lambda} gOn={s.gOn} lOn={s.lOn} onPick={onPick} />
      </div>

      <HelpDrawer open={help} onClose={closeHelp} />
    </div>
  );
}
