/** "How to read this" — a slide-over drawer so the explanation is one click away without
 *  taking dashboard space. */
import { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";

export function HelpDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return;
    const k = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    addEventListener("keydown", k); return () => removeEventListener("keydown", k);
  }, [open, onClose]);
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div className="backdrop" onClick={onClose} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} />
          <motion.aside className="drawer" role="dialog" aria-modal="true" aria-label="How to read this dashboard"
            initial={{ x: 40, opacity: 0 }} animate={{ x: 0, opacity: 1 }} exit={{ x: 40, opacity: 0 }} transition={{ duration: 0.28, ease: [0.2, 0.8, 0.2, 1] }}>
            <button className="close" onClick={onClose} aria-label="Close">×</button>
            <h3>How to read this</h3>
            <p className="lead">A bank can't fund everyone. AI prices each customer's risk; the optimiser finds the most profitable group that fits the budget.</p>

            <div className="sec">
              <h2>The floor</h2>
              <p>Each person is a <b>real credit-card customer</b> from a 30,000-account dataset. Hover anyone for their default probability and expected value.</p>
              <p>Funded people step onto the lit stage and raise their arms; the rest stand back, faded. <b>Coin stacks</b> show how much capital each needs. The <b>red floor ring</b> is their risk. <b>Beams</b> between funded people are the live coupling terms of the Hamiltonian: teal for same segment (diversification), plum for opposite group (fairness).</p>
            </div>

            <div className="sec">
              <h2>The two modes</h2>
              <ul>
                <li><b>Optimiser</b> — the solver chooses. Change the pool, budget or rules and it re-solves instantly.</li>
                <li><b>You vs optimiser</b> — <em>you</em> choose. Click people to fund them, stay under budget, and try to match the optimiser. The number of possible books doubles with every customer.</li>
              </ul>
            </div>

            <div className="sec">
              <h2>Profit across every budget</h2>
              <p>The optimiser run at every budget level, solved exactly. The gold dot is where the budget slider is now. The curve <b>bends over</b>: the first units of capital fund the best customers, and each extra unit buys progressively worse risk-adjusted value.</p>
            </div>

            <div className="sec">
              <h2>Energy landscape</h2>
              <p>Every possible portfolio — all 2ⁿ of them — scored by the <span className="q">Ising Hamiltonian</span> and sorted. Lower energy means more profit, by construction. The gold point is the <b>ground state</b>: the optimal book. The grey band is books that break the budget; their penalty pushes them to the top.</p>
              <p>This page draws the whole landscape by exact enumeration, which is instant at n ≤ 12. <span className="q">QAOA</span>, the quantum approximate solver, runs in the project's Python backend and is benchmarked against this exact answer there. It never sees this picture — it has to find the dot without it.</p>
            </div>

            <div className="sec">
              <h2>The readouts</h2>
              <ul>
                <li><b>Concentration</b> — Herfindahl index of the funded book across segments. 0 = spread out, 1 = all in one basket.</li>
                <li><b>Approval gap (F − M)</b> — approval rate of women minus men. Near zero is fair.</li>
                <li><b>Cost cards</b> — with a rule on, the profit given up against the unconstrained optimum. Fairness isn't claimed; it's priced.</li>
                <li><b>Greedy vs optimum</b> — how close the bank's usual rule of thumb gets to the true best.</li>
              </ul>
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
