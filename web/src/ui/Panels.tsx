import { motion, animate } from "framer-motion";
import { useEffect, useRef } from "react";
import type { Problem, Bits, Solution } from "../lib/problem";
import { profit, used, concentration, parityGap, objective } from "../lib/problem";
import { SECTOR_COLOR } from "../scene/Person";

/** Animated number that tweens between values. */
export function Num({ value, prefix = "", suffix = "", digits = 0 }: { value: number; prefix?: string; suffix?: string; digits?: number }) {
  const ref = useRef<HTMLSpanElement>(null!); const prev = useRef(0);
  useEffect(() => {
    const ctrl = animate(prev.current, value, { duration: 0.6, ease: "easeOut", onUpdate: v => { ref.current.textContent = prefix + v.toLocaleString(undefined, { maximumFractionDigits: digits, minimumFractionDigits: digits }) + suffix; } });
    prev.current = value; return () => ctrl.stop();
  }, [value, prefix, suffix, digits]);
  return <span ref={ref} />;
}

export interface ControlsState { n: number; budgetFrac: number; gOn: boolean; gamma: number; lOn: boolean; lambda: number; seed: number; mode: "opt" | "man"; }

export function Controls({ s, set, onReset }: { s: ControlsState; set: (patch: Partial<ControlsState>) => void; onReset: () => void }) {
  return (
    <motion.aside className="rail left card ctl" initial={{ x: -24, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.5 }}>
      <h2>Mode</h2>
      <div className="seg" role="tablist">
        <button role="tab" aria-selected={s.mode === "opt"} className={s.mode === "opt" ? "on" : ""} onClick={() => set({ mode: "opt" })}>Optimiser</button>
        <button role="tab" aria-selected={s.mode === "man"} className={s.mode === "man" ? "on" : ""} onClick={() => set({ mode: "man" })}>You vs optimiser</button>
      </div>
      <p className="modeHelp">
        {s.mode === "opt"
          ? <><b>The machine chooses.</b> Adjust the pool, budget or rules and the optimiser re-solves instantly, picking the most profitable group that fits the budget.</>
          : <><b>You choose.</b> Click people on the floor to fund them. Stay under budget and try to match the optimiser's profit — it's harder than it looks.</>}
      </p>

      <h2>The problem</h2>
      <div className="ctl-row"><label>Customers in pool <b>{s.n}</b></label>
        <input type="range" min={6} max={12} step={1} value={s.n} onChange={e => set({ n: +e.target.value })} aria-label="Customers in pool" />
        <small>One qubit per customer, plus slack qubits for the budget.</small></div>
      <div className="ctl-row"><label>Capital budget <b>{Math.round(s.budgetFrac * 100)}%</b></label>
        <input type="range" min={0.2} max={0.9} step={0.05} value={s.budgetFrac} onChange={e => set({ budgetFrac: +e.target.value })} aria-label="Capital budget" />
        <small>Share of what everyone asks for. Under 100% forces a choice.</small></div>

      <h2>Portfolio rules</h2>
      <label className="toggle"><input type="checkbox" checked={s.gOn} onChange={e => set({ gOn: e.target.checked })} /> Diversify across segments</label>
      <div className={"ctl-row sub " + (s.gOn ? "on" : "")}><label>Risk aversion γ <b>{s.gamma.toLocaleString()}</b></label>
        <input type="range" min={0} max={120000} step={5000} value={s.gamma} onChange={e => set({ gamma: +e.target.value })} aria-label="Risk aversion gamma" /></div>
      <label className="toggle"><input type="checkbox" checked={s.lOn} onChange={e => set({ lOn: e.target.checked })} /> Enforce approval-rate fairness</label>
      <div className={"ctl-row sub " + (s.lOn ? "on" : "")}><label>Fairness weight λ <b>{s.lambda.toLocaleString()}</b></label>
        <input type="range" min={0} max={800000} step={25000} value={s.lambda} onChange={e => set({ lambda: +e.target.value })} aria-label="Fairness weight lambda" /></div>

      <div className="ctl-row"><label>Draw a different pool <b>#{s.seed}</b></label>
        <input type="range" min={0} max={19} step={1} value={s.seed} onChange={e => set({ seed: +e.target.value })} aria-label="Instance seed" />
        <small>Re-samples real applicants from the 48 embedded. Nothing is cherry-picked.</small></div>
      {s.mode === "man" && <button className="btn ghost" onClick={onReset}>Reset selection</button>}
    </motion.aside>
  );
}

/** Colour key, drawn over the bottom of the stage so it sits next to what it explains. */
export function Legend() {
  return (
    <div className="legend-bar" aria-hidden="true">
      <span><i style={{ background: "#E9B949" }} />Funded · on stage</span>
      <span><i style={{ background: "#C9CBCF" }} />Declined · faded</span>
      <span><i style={{ background: "#E0553C" }} />Floor ring = default risk</span>
      <span><i style={{ background: "#0F7C8C" }} />Beam = quantum coupling</span>
      {Object.entries(SECTOR_COLOR).filter(([k]) => k !== "other").map(([k, c]) => <span key={k}><i style={{ background: c }} />{k}</span>)}
    </div>
  );
}

function Meter({ label, value, text, frac, cls, pill }: { label: string; value: string; text?: string; frac: number; cls: string; pill?: string }) {
  return (
    <div className="meter">
      <div className="row"><span>{label} {pill && <span className={"pill " + cls}>{pill}</span>}</span><b>{value}</b></div>
      <div className={"bar " + cls}><i style={{ width: Math.max(0, Math.min(100, frac * 100)) + "%" }} /></div>
      {text && <small>{text}</small>}
    </div>
  );
}

export function Readouts({ P, best, greedy, unconstrained, shown, manual, gamma, lambda, gOn, lOn, onPick }:
  { P: Problem; best: Solution; greedy: Solution; unconstrained: Solution | null; shown: Bits; manual: Bits | null; gamma: number; lambda: number; gOn: boolean; lOn: boolean; onPick: (i: number) => void }) {
  const pr = profit(P, shown), u = used(P, shown), H = concentration(P, shown), G = parityGap(P, shown), aG = Math.abs(G);
  const hCls = H < 0.35 ? "ok" : H < 0.6 ? "warn" : "crit", gCls = aG < 0.1 ? "ok" : aG < 0.25 ? "warn" : "crit";
  const ratio = greedy.obj / Math.max(best.obj, 1e-9);
  const you = manual ? objective(P, manual, gamma, lambda) : null;
  const over = manual ? used(P, manual) > P.budget : false;
  const pct = you != null && best.obj > 0 ? Math.max(0, you) / best.obj : 0;
  return (
    <motion.aside className="rail right card read" initial={{ x: 24, opacity: 0 }} animate={{ x: 0, opacity: 1 }} transition={{ duration: 0.5 }}>
      <h2>Result</h2>
      <div className="big"><div className="l">Expected profit</div><div className="v"><Num value={pr} /><small>NT$</small></div></div>

      {manual && (
        <div className="game">
          <div className="vs">
            <div className="you"><div className="l">Your book</div><div className="v"><Num value={Math.max(0, profit(P, manual))} /></div></div>
            <div className="opt"><div className="l">Optimiser</div><div className="v"><Num value={profit(P, best.x)} /></div></div>
          </div>
          <div className="score">
            {over ? <span className="bad">Over budget by {used(P, manual) - P.budget} units — the bank can't fund this book.</span>
              : pct >= 0.999 ? <span className="gold">You found the ground state. That's the optimal book.</span>
              : <>You captured <b>{(pct * 100).toFixed(1)}%</b> of the optimiser's value with {manual.reduce((a, v) => a + v, 0)} customers. Keep going.</>}
          </div>
        </div>
      )}

      <Meter label="Capital used" value={`${u} / ${P.budget} units`} frac={u / P.budget} cls={u > P.budget ? "crit" : ""} />
      <Meter label="Concentration" value={H.toFixed(3)} frac={H} cls={hCls} pill={hCls === "ok" ? "diversified" : hCls === "warn" ? "concentrated" : "one basket"} />
      <Meter label="Approval gap (F − M)" value={(G >= 0 ? "+" : "") + G.toFixed(2)} frac={aG} cls={gCls} pill={gCls === "ok" ? "fair" : gCls === "warn" ? "skewed" : "unfair"} />

      {unconstrained && gOn && <div className="delta"><b>Diversifying</b> cut concentration {concentration(P, unconstrained.x).toFixed(2)} → {concentration(P, best.x).toFixed(2)} and cost <b>NT${Math.round(profit(P, unconstrained.x) - profit(P, best.x)).toLocaleString()}</b>.</div>}
      {unconstrained && lOn && <div className="delta"><b>Fairness</b> moved the approval gap {parityGap(P, unconstrained.x).toFixed(2)} → {parityGap(P, best.x).toFixed(2)} and cost <b>NT${Math.round(profit(P, unconstrained.x) - profit(P, best.x)).toLocaleString()}</b>.</div>}

      <div className="meter"><div className="row"><span>Greedy heuristic vs optimum</span><b>{(ratio * 100).toFixed(1)}%</b></div></div>

      <h2>The pool {manual && <span className="muted"> · click a row to fund</span>}</h2>
      <table className={"pool" + (manual ? " pick" : "")}>
        <colgroup><col className="c-id" /><col /><col className="c-p" /><col className="c-ev" /><col className="c-u" /><col className="c-b" /></colgroup>
        <thead><tr><th>#</th><th>Segment</th><th className="num" title="Default probability from the AI model">P(def)</th><th className="num" title="Expected value, NT$ thousands">EV</th><th className="num" title="Capital units of NT$20,000">U</th><th className="num book" title="Funded in the current book">Book</th></tr></thead>
        <tbody>
          {P.pool.map((p, i) => (
            <tr key={p.id} className={shown[i] ? "on" : "off"} onClick={manual ? () => onPick(i) : undefined}>
              <td className="id">{p.id}</td>
              <td className="seg"><i style={{ background: SECTOR_COLOR[p.sector as keyof typeof SECTOR_COLOR] ?? "#6E7683" }} />{p.sector.replace("high-school", "high sch.")} · {p.group[0].toUpperCase()}</td>
              <td className="num">{(p.p * 100).toFixed(0)}%</td>
              <td className={"num " + (p.ev < 0 ? "neg" : "")}>{Math.round(p.ev / 1000)}k</td>
              <td className="num">{p.units}</td>
              <td className="num book">{shown[i] ? "✓" : "·"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </motion.aside>
  );
}
