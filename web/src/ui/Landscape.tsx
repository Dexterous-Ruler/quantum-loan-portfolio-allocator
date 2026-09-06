/** Every one of the 2ⁿ portfolios, scored by the Hamiltonian's energy and sorted. The gold point is
 *  the ground state — by construction, the optimal loan book. The cyan marker is your own book in
 *  game mode. This is the genuine spectrum, computed by enumeration. */
import { useEffect, useRef } from "react";
import type { SpecEntry } from "../lib/problem";

export function Landscape({ spectrum, currentMask, n, qubits }: { spectrum: SpecEntry[]; currentMask: number | null; n: number; qubits: number }) {
  const ref = useRef<HTMLCanvasElement>(null!);
  useEffect(() => {
    const c = ref.current, ctx = c.getContext("2d")!;
    const draw = () => {
      const dpr = Math.min(devicePixelRatio, 2), W = c.clientWidth, H = c.clientHeight;
      c.width = W * dpr; c.height = H * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.clearRect(0, 0, W, H);
      const pad = { l: 8, r: 8, t: 12, b: 18 }, iw = W - pad.l - pad.r, ih = H - pad.t - pad.b;
      const feas = spectrum.filter(s => s.feasible); if (!feas.length) return;
      const eMin = feas[0].e, eMax = feas[feas.length - 1].e, span = Math.max(1, eMax - eMin);
      const N = spectrum.length, cols = Math.min(N, Math.floor(iw)), per = N / cols;
      ctx.strokeStyle = "#243050"; ctx.lineWidth = 1;
      for (let k = 0; k <= 4; k++) { const y = pad.t + ih * k / 4; ctx.beginPath(); ctx.moveTo(pad.l, y); ctx.lineTo(W - pad.r, y); ctx.stroke(); }
      const curIdx = currentMask == null ? -1 : spectrum.findIndex(s => s.mask === currentMask);
      let curX: number | null = null;
      for (let col = 0; col < cols; col++) {
        const i = Math.floor(col * per), s = spectrum[i];
        const v = s.feasible ? Math.min(1, (s.e - eMin) / span) : 1;
        const h = Math.max(1.5, (1 - v) * ih * 0.92);
        ctx.globalAlpha = s.feasible ? 0.85 : 0.45; ctx.fillStyle = s.feasible ? "#5EE7F0" : "#33405F";
        ctx.fillRect(pad.l + col * (iw / cols), pad.t + ih - h, Math.max(1, iw / cols - 0.4), h);
        if (curIdx >= 0 && i <= curIdx && curIdx < Math.floor((col + 1) * per)) curX = pad.l + col * (iw / cols);
      }
      ctx.globalAlpha = 1;
      ctx.fillStyle = "#F2B84B"; ctx.beginPath(); ctx.arc(pad.l + 2, pad.t + ih - ih * 0.92, 5, 0, 7); ctx.fill();
      ctx.font = '500 10.5px "IBM Plex Mono", monospace'; ctx.fillText("ground state = optimal book", pad.l + 12, pad.t + ih - ih * 0.92 + 4);
      ctx.fillStyle = "#7E89A8"; ctx.fillText(`2^${n} = ${N.toLocaleString()} configurations · ${qubits} qubits · sorted by energy →`, pad.l, H - 5);
      ctx.textAlign = "right"; ctx.fillText("lower = better", W - pad.r, H - 5); ctx.textAlign = "left";
      if (curX != null) { ctx.strokeStyle = "#C9A0FF"; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(curX + 1, pad.t); ctx.lineTo(curX + 1, pad.t + ih); ctx.stroke(); ctx.fillStyle = "#C9A0FF"; ctx.fillText("your book", Math.min(curX + 6, W - 70), pad.t + 10); }
    };
    draw();
    const ro = new ResizeObserver(draw); ro.observe(c);
    return () => ro.disconnect();
  }, [spectrum, currentMask, n, qubits]);
  return <canvas ref={ref} className="land" />;
}
