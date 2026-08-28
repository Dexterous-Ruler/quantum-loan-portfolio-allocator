"""Animated GIF of the core interaction, for the README and as demo insurance.

Sweeps the capital budget and renders, per frame, the funded portfolio alongside its
position on the profit curve. This is the "money shot" of the live demo captured as a
file, so a failed projector or a dead tunnel does not cost the whole presentation.

Solved exactly rather than with QAOA: the animation is about the allocation problem, and
15 QAOA solves would take two minutes and add sampling jitter that reads as a rendering
bug rather than as physics.

    python src/make_demo_gif.py       # ~20 seconds
"""
from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
from PIL import Image  # noqa: E402

import portfolio as pf  # noqa: E402
import solvers  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
ARTIFACTS = ROOT / "artifacts"
OUT = ARTIFACTS / "demo.gif"

QCOL, GREY, ACC, INK = "#4c6ef5", "#c9ccd6", "#e8833a", "#1a1a1a"
POOL_N, SEED = 10, 0


def _bare(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_axisbelow(True)


def main() -> None:
    scored = pd.read_csv(ARTIFACTS / "scored_applicants.csv")

    fracs = np.round(np.arange(0.20, 0.92, 0.05), 2)
    states = []
    for f in fracs:
        p = pf.build_problem(scored, n=POOL_N, budget_fraction=float(f),
                             fairness_lambda=0.0, seed=SEED)
        x = solvers.solve_bruteforce(p).x
        states.append((p, x, float(p.ev @ x)))

    # One consistent applicant ordering across all frames, or bars jump between frames and
    # the animation is unreadable.
    base = states[0][0]
    order = np.argsort(base.ev)
    labels = [f"#{base.ids[i]}" for i in order]
    units = base.units[order]
    budgets = [s[0].budget_units for s in states]
    profits = [s[2] for s in states]

    frames = []
    for (p, x, profit) in states:
        fig, (a1, a2) = plt.subplots(1, 2, figsize=(9.6, 3.7), dpi=110)

        funded = x[order] == 1
        a1.barh(range(len(units)), units,
                color=[QCOL if f else GREY for f in funded], edgecolor="none")
        a1.set_yticks(range(len(units)))
        a1.set_yticklabels(labels, fontsize=8)
        a1.set_xlabel("Capital units requested")
        a1.set_xlim(0, max(units) * 1.25)
        a1.set_title(f"Funded (blue) vs declined (grey)\n"
                     f"{int(p.units @ x)} of {p.budget_units} units deployed  ·  "
                     f"{profit:,.0f} DM",
                     fontsize=9.5, loc="left", color=INK)
        a1.grid(axis="x", alpha=0.25, linewidth=0.6)
        _bare(a1)

        a2.plot(budgets, profits, "-", color=QCOL, linewidth=2, zorder=3)
        a2.scatter(budgets, profits, s=16, color=QCOL, zorder=4)
        a2.scatter([p.budget_units], [profit], s=170, color=ACC, zorder=5,
                   edgecolor="white", linewidth=1.8)
        a2.set_xlabel("Capital budget (units)")
        a2.set_ylabel("Expected profit (DM)")
        a2.set_ylim(min(profits) * 0.92, max(profits) * 1.08)
        a2.set_title("Profit against budget\nDiminishing returns as capital grows",
                     fontsize=9.5, loc="left", color=INK)
        a2.grid(alpha=0.25, linewidth=0.6)
        _bare(a2)

        fig.tight_layout()
        fig.canvas.draw()
        # tostring_rgb() was removed in recent matplotlib; buffer_rgba() is the supported
        # path. Drop the alpha channel for GIF.
        frames.append(Image.frombytes("RGBA", fig.canvas.get_width_height(),
                                      bytes(fig.canvas.buffer_rgba())).convert("RGB"))
        plt.close(fig)

    # Ping-pong so the loop reads as a slider being dragged back and forth.
    seq = frames + frames[-2:0:-1]
    seq[0].save(OUT, save_all=True, append_images=seq[1:], duration=280, loop=0, optimize=True)
    print(f"wrote {OUT.relative_to(ROOT)} ({OUT.stat().st_size / 1024:.0f} KB, {len(seq)} frames)")


if __name__ == "__main__":
    main()
