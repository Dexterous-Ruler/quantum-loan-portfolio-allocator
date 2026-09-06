/** Every one of the 2ⁿ portfolios, scored by the Hamiltonian's energy and sorted, drawn as an
 *  area chart. The gold point is the ground state — by construction, the optimal loan book. The
 *  plum marker is your own book in game mode. Infeasible (over-budget) configurations are shown
 *  as the greyed band at the top. This is the genuine spectrum, computed by enumeration.
 *  The canvas is absolutely positioned inside its box and redraws on resize, so it fills any card. */
import { useEffect, useRef } from "react";
import type { SpecEntry } from "../lib/problem";

export function Landscape({ spectrum, currentMask, n, qubits }: { spectrum: SpecEntry[]; currentMask: number | null; n: number; qubits: number }) {
  const ref = useRef<HTMLCanvasElement>(null!);
  useEffect(() => {
    const c = ref.current, ctx = c.getContext("2d")!;
    const draw = () => {
      const dpr = Math.min(devicePixelRatio, 2), W = c.clientWidth, H = c.clientHeight;
      if (!W || !H) return;
      c.width = W * dpr; c.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
      const pad = { l: 10, r: 12, t: 16, b: 22 }, iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
      const feas = spectrum.filter(s => s.feasible); if (!feas.length) return;
      const eMin = feas[0].e, eMax = feas[feas.length - 1].e, span = Math.max(1, eMax - eMin);
      const N = spectrum.length, cols = Math.min(N, Math.floor(iw)), per = N / cols;
      const nFeas = feas.length, feasW = (nFeas / N) * iw;

      // grid
      ctx.strokeStyle = "#E7E6E0"; ctx.lineWidth = 1;
      for (let k = 0; k <= 4; k++) { const y = pad.t + ih * k / 4; ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke(); }
      // infeasible band (over budget) — greyed, at the top
      if (nFeas < N) { ctx.fillStyle = "#EFEEE9"; ctx.fillRect(pad.l + feasW, pad.t, iw - feasW, ih); ctx.fillStyle = "#9AA0A8"; ctx.font = '500 10px "DM Mono", monospace'; ctx.textAlign = "right"; ctx.fillText("over budget · infeasible", W - pad.r - 4, pad.t + 12); ctx.textAlign = "left"; }

      // feasible energy curve: sample per column
      const yAt = (s: SpecEntry) => pad.t + ih - (1 - Math.min(1, (s.e - eMin) / span)) * ih * 0.9;
      const pts: [number, number][] = [];
      for (let col = 0; col < cols; col++) { const i = Math.floor(col * per); const s = spectrum[i]; if (!s.feasible) break; pts.push([pad.l + col * (iw / cols), yAt(s)]); }
      if (pts.length > 1) {
        const grad = ctx.createLinearGradient(0, pad.t, 0, pad.t + ih); grad.addColorStop(0, "rgba(15,124,140,0.30)"); grad.addColorStop(1, "rgba(15,124,140,0.02)");
        ctx.beginPath(); ctx.moveTo(pts[0][0], pad.t + ih); pts.forEach(p => ctx.lineTo(p[0], p[1])); ctx.lineTo(pts[pts.length - 1][0], pad.t + ih); ctx.closePath(); ctx.fillStyle = grad; ctx.fill();
        ctx.beginPath(); pts.forEach((p, i) => i ? ctx.lineTo(p[0], p[1]) : ctx.moveTo(p[0], p[1])); ctx.strokeStyle = "#0F7C8C"; ctx.lineWidth = 2; ctx.lineJoin = "round"; ctx.stroke();
      }
      // ground state marker with leader
      const gx = pad.l + 3, gy = yAt(feas[0]);
      ctx.strokeStyle = "#C4841D"; ctx.lineWidth = 1; ctx.setLineDash([2, 3]); ctx.beginPath(); ctx.moveTo(gx, gy); ctx.lineTo(gx + 54, gy - 14); ctx.stroke(); ctx.setLineDash([]);
      ctx.fillStyle = "#E9B949"; ctx.strokeStyle = "#FFFFFF"; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(gx, gy, 5.5, 0, 7); ctx.fill(); ctx.stroke();
      ctx.font = '500 10.5px "DM Mono", monospace'; ctx.fillStyle = "#C4841D"; ctx.fillText("ground state · optimal book", gx + 58, gy - 11);
      // axis captions
      ctx.fillStyle = "#7A8089"; ctx.font = '400 10px "DM Mono", monospace';
      ctx.fillText(`2^${n} = ${N.toLocaleString()} portfolios · ${qubits} qubits · sorted by energy →`, pad.l, H - 6);
      ctx.textAlign = "right"; ctx.fillText("lower = better", W - pad.r, H - 6); ctx.textAlign = "left";
      // your book (game mode)
      if (currentMask != null) {
        const idx = spectrum.findIndex(s => s.mask === currentMask);
        if (idx >= 0) { const cx = pad.l + (idx / per) * (iw / cols); ctx.strokeStyle = "#8B3A62"; ctx.lineWidth = 1.5; ctx.beginPath(); ctx.moveTo(cx, pad.t); ctx.lineTo(cx, pad.t + ih); ctx.stroke();
          ctx.fillStyle = "#8B3A62"; ctx.font = '500 10.5px "DM Mono", monospace'; ctx.fillText("your book", Math.min(cx + 6, W - 72), pad.t + 27); }
      }
    };
    draw();
    const ro = new ResizeObserver(draw); ro.observe(c);
    return () => ro.disconnect();
  }, [spectrum, currentMask, n, qubits]);
  return <div className="chartbox"><canvas ref={ref} className="land" /></div>;
}
