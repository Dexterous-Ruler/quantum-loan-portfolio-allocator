/** Profit achievable at every budget level, solved exactly. The marked point is the current
 *  budget. Read it as a diminishing-returns curve: past a point, extra capital buys progressively
 *  less because the remaining applicants carry worse risk-adjusted value.
 *  The SVG is drawn at the measured pixel size of its box so text stays crisp at any card size. */
import { useEffect, useRef, useState } from "react";

export interface CurvePt { frac: number; budget: number; profit: number; }

export function ProfitCurve({ pts, current }: { pts: CurvePt[]; current: number }) {
  const box = useRef<HTMLDivElement>(null!);
  const [sz, setSz] = useState({ w: 320, h: 140 });
  useEffect(() => {
    const ro = new ResizeObserver(([e]) => { const r = e.contentRect; if (r.width > 20 && r.height > 20) setSz({ w: r.width, h: r.height }); });
    ro.observe(box.current); return () => ro.disconnect();
  }, []);
  const W = sz.w, H = sz.h, pl = 42, pr = 16, pt = 14, pb = 24;
  const iw = W - pl - pr, ih = H - pt - pb;
  const xs = pts.map(p => p.budget), ys = pts.map(p => p.profit);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = 0, y1 = Math.max(1, ...ys) * 1.06;
  const X = (b: number) => pl + ((b - x0) / Math.max(1, x1 - x0)) * iw;
  const Y = (v: number) => pt + ih - ((v - y0) / (y1 - y0)) * ih;
  const line = pts.map((p, i) => `${i ? "L" : "M"}${X(p.budget).toFixed(1)},${Y(p.profit).toFixed(1)}`).join(" ");
  const area = `${line} L${X(x1).toFixed(1)},${(pt + ih).toFixed(1)} L${X(x0).toFixed(1)},${(pt + ih).toFixed(1)} Z`;
  const cur = pts.find(p => p.budget === current) ?? pts.reduce((a, b) => Math.abs(b.budget - current) < Math.abs(a.budget - current) ? b : a);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(t => y0 + (y1 - y0) * t);
  const fmt = (v: number) => v >= 1000 ? (v / 1000).toFixed(0) + "k" : v.toFixed(0);
  const lblX = Math.min(Math.max(X(cur.budget), pl + 60), W - pr - 60);
  return (
    <div className="chartbox" ref={box} aria-label="Expected profit at every budget level">
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} role="img">
        <defs>
          <linearGradient id="pcFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0F7C8C" stopOpacity="0.26" /><stop offset="100%" stopColor="#0F7C8C" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {ticks.map((t, i) => <g key={i}><line x1={pl} x2={W - pr} y1={Y(t)} y2={Y(t)} stroke="#E7E6E0" strokeWidth="1" />
          <text x={pl - 7} y={Y(t) + 3.5} fontSize="10" fontFamily="DM Mono, monospace" fill="#7A8089" textAnchor="end">{fmt(t)}</text></g>)}
        <path d={area} fill="url(#pcFill)" />
        <path d={line} fill="none" stroke="#0F7C8C" strokeWidth="2" strokeLinejoin="round" strokeLinecap="round" />
        {pts.map((p, i) => <circle key={i} cx={X(p.budget)} cy={Y(p.profit)} r="2.2" fill="#0F7C8C" />)}
        <line x1={X(cur.budget)} x2={X(cur.budget)} y1={pt} y2={pt + ih} stroke="#C4841D" strokeWidth="1" strokeDasharray="2 3" />
        <circle cx={X(cur.budget)} cy={Y(cur.profit)} r="5.5" fill="#E9B949" stroke="#FFFFFF" strokeWidth="2" />
        <text x={lblX} y={pt + 9} fontSize="10.5" fontFamily="DM Mono, monospace" fontWeight="500" fill="#C4841D" textAnchor="middle">now · {cur.budget} units · NT${Math.round(cur.profit).toLocaleString()}</text>
        <text x={pl} y={H - 7} fontSize="10" fontFamily="DM Mono, monospace" fill="#7A8089">{x0} units</text>
        <text x={pl + iw / 2} y={H - 7} fontSize="10" fontFamily="DM Mono, monospace" fill="#7A8089" textAnchor="middle">capital budget →</text>
        <text x={W - pr} y={H - 7} fontSize="10" fontFamily="DM Mono, monospace" fill="#7A8089" textAnchor="end">{x1} units</text>
      </svg>
    </div>
  );
}
