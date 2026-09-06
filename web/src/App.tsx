import { useCallback, useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { samplePool, solveExact, solveGreedy, maskOf, profit, type Bits } from "./lib/problem";
import { Scene } from "./scene/Scene";
import { Controls, Readouts, Num, type ControlsState } from "./ui/Panels";
import { Landscape } from "./ui/Landscape";

const REDUCED = typeof matchMedia !== "undefined" && matchMedia("(prefers-reduced-motion: reduce)").matches;

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

  useEffect(() => { setManual(new Array(P.n).fill(0)); }, [P]);
  useEffect(() => { if (s.mode !== "opt") return; setTick(t => t + 1); setFlash(true); const id = setTimeout(() => setFlash(false), 1500); return () => clearTimeout(id); }, [best, s.mode]);

  const man = s.mode === "man" ? manual : null;
  const shown = man ?? best.x;
  const onPick = useCallback((i: number) => setManual(m => { const c = m.slice(); c[i] = c[i] ? 0 : 1; return c; }), []);

  return (
    <div className="app">
      <motion.header initial={{ y: -16, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.5 }}>
        <div className="brand">
          <h1>Quantum Loan Book</h1>
          <p>Which borrowers should a bank fund when it can't fund them all? AI prices the risk; the optimiser finds the ground state.</p>
        </div>
        <div className="kpis">
          <div className="kpi"><div className="l">Customers</div><div className="v">{P.n}</div></div>
          <div className="kpi"><div className="l">Budget</div><div className="v">{P.budget} units</div></div>
          <div className="kpi cyan"><div className="l">Qubits</div><div className="v">{P.qubits}</div></div>
          <div className="kpi gold"><div className="l">Optimal profit</div><div className="v"><Num value={profit(P, best.x)} prefix="NT$ " /></div></div>
        </div>
      </motion.header>

      <Controls s={s} set={set} onReset={() => setManual(new Array(P.n).fill(0))} />

      <main className="stage">
        <Scene P={P} x={best.x} manual={man} gOn={s.gOn} lOn={s.lOn} solveTick={solveTick} onPick={onPick} reduced={REDUCED} />
        <AnimatePresence>{flash && s.mode === "opt" && (
          <motion.div className="flash" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>Ground state found</motion.div>
        )}</AnimatePresence>
        <div className="hint">{s.mode === "man" ? "Click people to fund them · stay under budget · try to reach the ground state" : "Drag to orbit · scroll to zoom · hover a person · switch to game mode to try it yourself"}</div>
      </main>

      <Readouts P={P} best={best} greedy={greedy} unconstrained={unconstrained} shown={shown} manual={man} gamma={gamma} lambda={lambda} gOn={s.gOn} lOn={s.lOn} />

      <footer>
        <div className="landWrap">
          <div className="landHead"><h2>Energy landscape — every possible portfolio</h2></div>
          <Landscape spectrum={best.spectrum} currentMask={man ? maskOf(man) : null} n={P.n} qubits={P.qubits} />
        </div>
        <div className="note">
          <b>What this is.</b> Every one of the 2ⁿ ways to fund the pool, scored by the <span className="q">Ising Hamiltonian's energy</span> and sorted. Lower is better. The gold point is the <b>ground state</b> — the lowest-energy configuration — and by construction it <i>is</i> the optimal loan book.<br /><br />
          <b>Honest note.</b> This page runs the exact ground-truth solver (enumerating all 2ⁿ portfolios — instant at n ≤ 12) on real applicant data. <span className="q">QAOA</span>, the quantum approximate solver, runs in the project's Python backend and is benchmarked against this exact answer there.
        </div>
      </footer>
    </div>
  );
}
