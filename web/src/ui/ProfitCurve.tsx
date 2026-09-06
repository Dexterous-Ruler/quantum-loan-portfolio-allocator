/** Profit achievable at every budget level, solved exactly. The marked point is the current
 *  budget. Read it as a diminishing-returns curve: past a point, extra capital buys progressively
 *  less because the remaining applicants carry worse risk-adjusted value. */
export interface CurvePt { frac: number; budget: number; profit: number; }

export function ProfitCurve({ pts, current }: { pts: CurvePt[]; current: number }) {
  const W = 300, H = 118, pl = 34, pr = 10, pt = 10, pb = 22;
  const iw = W - pl - pr, ih = H - pt - pb;
  const xs = pts.map(p => p.budget), ys = pts.map(p => p.profit);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), y0 = 0, y1 = Math.max(1, ...ys) * 1.06;
  const X = (b: number) => pl + ((b - x0) / Math.max(1, x1 - x0)) * iw;
  const Y = (v: number) => pt + ih - ((v - y0) / (y1 - y0)) * ih;
  const line = pts.map((p, i) => `${i ? "L" : "M"}${X(p.budget).toFixed(1)},${Y(p.profit).toFixed(1)}`).join(" ");
  const area = `${line} L${X(x1).toFixed(1)},${(pt + ih).toFixed(1)} L${X(x0).toFixed(1)},${(pt + ih).toFixed(1)} Z`;
  const cur = pts.find(p => p.budget === current) ?? pts.reduce((a, b) => Math.abs(b.budget - current) < Math.abs(a.budget - current) ? b : a);
  const ticks = [0, 0.5, 1].map(t => y0 + (y1 - y0) * t);
  const fmt = (v: number) => v >= 1000 ? (v / 1000).toFixed(0) + "k" : v.toFixed(0);
  return (
    <div className="chart" aria-label="Expected profit at every budget level">
      <svg viewBox={`0 0 ${W} ${H}`} role="img">
        <defs>
          <linearGradient id="pcFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0F7C8C" stopOpacity="0.28" /><stop offset="100%" stopColor="#0F7C8C" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {ticks.map((t, i) => <g key={i}><line x1={pl} x2={W - pr} y1={Y(t)} y2={Y(t)} stroke="#E7E6E0" strokeWidth="1" />
          <text x={pl - 6} y={Y(t) + 3.5} fontSize="9" fontFamily="DM Mono, monospace" fill="#7A8089" textAnchor="end">{fmt(t)}</text></g>)}
        <path d={area} fill="url(#pcFill)" />
        <path d={line} fill="none" stroke="#0F7C8C" strokeWidth="1.8" strokeLinejoin="round" strokeLinecap="round" />
        {pts.map((p, i) => <circle key={i} cx={X(p.budget)} cy={Y(p.profit)} r="1.8" fill="#0F7C8C" />)}
        <line x1={X(cur.budget)} x2={X(cur.budget)} y1={pt} y2={pt + ih} stroke="#C4841D" strokeWidth="1" strokeDasharray="2 3" />
        <circle cx={X(cur.budget)} cy={Y(cur.profit)} r="5" fill="#E9B949" stroke="#FFFFFF" strokeWidth="2" />
        <text x={pl} y={H - 6} fontSize="9" fontFamily="DM Mono, monospace" fill="#7A8089">{x0} units</text>
        <text x={W - pr} y={H - 6} fontSize="9" fontFamily="DM Mono, monospace" fill="#7A8089" textAnchor="end">{x1} units</text>
      </svg>
      <div className="cap"><span>profit vs. capital budget</span><span>now: {cur.budget} units → NT${Math.round(cur.profit).toLocaleString()}</span></div>
    </div>
  );
}
