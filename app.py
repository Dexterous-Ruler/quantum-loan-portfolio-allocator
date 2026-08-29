"""Deliverable 3 -- the live demo.

Run with:  .venv\\Scripts\\streamlit run app.py

The jury interaction is: move the capital budget slider, watch the quantum optimiser
re-allocate the loan book in real time; toggle the fairness penalty, watch the
approval-rate gap close and the profit cost of closing it appear.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))

import portfolio as pf  # noqa: E402
import solvers  # noqa: E402

ARTIFACTS = Path(__file__).parent / "artifacts"

st.set_page_config(page_title="Quantum Loan-Portfolio Allocator", layout="wide")


@st.cache_data
def load_scored() -> pd.DataFrame:
    return pd.read_csv(ARTIFACTS / "scored_applicants.csv")


@st.cache_data
def load_ai_metrics() -> dict:
    import json

    return json.loads((ARTIFACTS / "ai_metrics.json").read_text())


st.title("Quantum-Assisted Loan-Portfolio Allocator")
st.caption(
    "A bank has more creditworthy customers than capital. This picks which subset to fund — "
    "using a classical AI model to price the risk and a **quantum** optimiser to choose the book."
)

with st.expander("📖  What is this, and what am I looking at?  — read me first", expanded=False):
    st.markdown("""
### The problem in one sentence
A lender has 6,000 viable credit-card customers but only enough capital for a handful.
**Which subset should it fund?** That is a *0-1 knapsack* — pick items with the best value
that fit in a bag — and it is NP-hard, which is why it is worth pointing a quantum computer at.

### The pipeline, step by step

| # | Stage | What happens | Why it matters |
|---|---|---|---|
| 1 | **Real data** | 30,000 real Taiwanese credit-card accounts (2005), 22.1% of which defaulted | Nothing here is synthetic |
| 2 | **AI model** | A gradient-boosted classifier predicts `P(default)` for each customer | This is the "AI" half |
| 3 | **Money** | `EV = P(repay)×interest − P(default)×loss` per customer | Turns a probability into an amount |
| 4 | **QUBO** | Maximise total EV, minus risk and fairness penalties, subject to a capital budget | The optimisation problem |
| 5 | **Quantum** | The QUBO becomes an Ising Hamiltonian; **QAOA** searches for its lowest-energy state | This is the "quantum" half |
| 6 | **Answer** | The winning bitstring *is* the list of customers to fund | |

### The key idea
Most hybrid projects run AI and quantum **side by side** — train a classifier, then train a
quantum classifier, compare the two. Ours run **in series**: the AI model's output *becomes*
the quantum problem's coefficients. Delete the AI and there is no quantum problem left.

### What we honestly found
Quantum does **not** beat classical here, and we say so on the results page. At 14 qubits an
ordinary exhaustive search is hundreds of times faster and always exact. What this demonstrates
is a *correct end-to-end mapping* and an honest measurement of where it breaks — which is what
the brief asked for ("small qubit counts, simulator only").
""")

scored = load_scored()
metrics = load_ai_metrics()

# ------------------------------------------------------------------ controls
with st.sidebar:
    st.header("Controls")
    st.caption("Every control below changes the *problem*, and the optimiser re-solves it.")
    pool_n = st.select_slider("Customers in pool", options=[6, 8, 10, 12], value=10,
                              help="Qubit count = applicants + binary slack for the budget inequality, "
                                   "roughly n + 4. Shown live in the metric above.")
    budget_fraction = st.slider("Capital budget (fraction of total requested)", 0.20, 0.90, 0.45, 0.05,
                                help="How much capital the bank has, as a share of what all "
                                     "customers together want. 0.45 means it can fund under "
                                     "half the book — so the optimiser must choose.")
    # Default p=1. Across repeated QAOA seeds the depths are statistically indistinguishable
    # -- the apparent "best depth" flipped between benchmark runs -- so we take the cheapest
    # one rather than pretending a winner exists. See DELIVERABLE_4.md, table A.
    reps = st.select_slider("QAOA depth p", options=[1, 2, 3], value=1,
                            help="How many layers deep the quantum circuit goes. In theory "
                                 "deeper searches better; we measured that at this size the "
                                 "difference is smaller than the run-to-run noise, so we "
                                 "default to the cheapest.")
    risk_on = st.toggle("Diversify across segments", value=False,
                        help="Stops the optimiser piling all the capital into one customer "
                             "segment. Segments default together in a downturn, so a "
                             "concentrated book is fragile. This is the classic Markowitz "
                             "risk term — and it costs zero extra qubits.")
    risk_gamma = st.slider("Risk aversion gamma", 0, 120000, 40000, 5000, disabled=not risk_on,
                           help="Higher = the bank cares more about spreading capital across "
                                "customer segments than about raw profit.")
    fairness_on = st.toggle("Enforce approval-rate fairness", value=False,
                            help="Pushes the approval rate for men and women toward equality. "
                                 "A pure profit-maximiser has no reason to do this, so it has "
                                 "to be written into the objective. Costs zero extra qubits.")
    fairness_lambda = st.slider("Fairness weight lambda", 0, 800000, 200000, 25000,
                                disabled=not fairness_on,
                                help="Higher = the bank cares more about approving men and "
                                     "women at equal rates than about raw profit.")
    seed = st.number_input("Instance seed", 0, 999, 0, 1,
                           help="Draws a different random pool of customers. Change it to "
                                "confirm nothing here is cherry-picked.")
    go = st.button("Optimise portfolio", type="primary", width="stretch")

GAMMA = float(risk_gamma) if risk_on else 0.0
LAMBDA = float(fairness_lambda) if fairness_on else 0.0

problem = pf.build_problem(
    scored, n=pool_n, budget_fraction=budget_fraction,
    fairness_lambda=LAMBDA, risk_gamma=GAMMA, seed=int(seed),
)
_, n_qubits = pf.qubo_and_qubits(problem)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Customers in pool", problem.n,
          help="How many candidate accounts the optimiser is choosing between. Each one "
               "becomes a yes/no decision — and therefore one qubit.")
c2.metric("Capital budget", f"{problem.budget_units} units",
          help=f"Total capital available, in units of NT${pf.UNIT_SIZE:,.0f} of exposure. "
               "The optimiser cannot exceed this — it is the constraint that makes the "
               "problem hard.")
c3.metric("Qubits", n_qubits,
          help="Customers + extra qubits to encode the budget constraint. A quantum computer "
               "would need this many. Above ~30, simulating it becomes impossible on a laptop.")
c4.metric("AI model AUC", f"{metrics['gbm_auc']:.3f}",
          help="How well the risk model separates defaulters from non-defaulters. 0.5 = coin "
               "flip, 1.0 = perfect. Around 0.78 is normal for credit scoring.")

# ------------------------------------------------------------------ applicants
st.subheader("1. The AI model prices each customer")
st.caption(
    "The classifier read each customer's payment history and produced **P(default)**. "
    "Combined with their outstanding balance, that gives **expected value** — what the bank "
    "expects to earn (or lose) by funding them. Red = riskier. These numbers are the input "
    "to the quantum step; nothing below is hand-picked."
)
view = problem.meta[["LIMIT_BAL", "principal", "AGE", "group", "sector",
                     "p_default", "expected_value"]].copy()
view.insert(0, "applicant", [f"#{i}" for i in problem.ids])
view["capital_units"] = problem.units
view = view.rename(columns={"p_default": "P(default)", "expected_value": "expected value (NT$)",
                            "LIMIT_BAL": "credit limit", "principal": "exposure",
                            "AGE": "age"})
st.dataframe(
    view.style.format({"P(default)": "{:.1%}", "expected value (NT$)": "{:,.0f}", "credit limit": "{:,.0f}", "exposure": "{:,.0f}"})
        .background_gradient(subset=["P(default)"], cmap="Reds"),
    width="stretch", hide_index=True,
)

@st.cache_data(show_spinner=False)
def cached_qaoa(pool_n: int, budget_fraction: float, lam: float, seed: int, reps: int,
                gamma: float = 0.0):
    """Cache by the control values, so re-showing a configuration during a demo is instant.

    Rebuilds the problem inside rather than taking it as an argument: Streamlit would have to
    hash the whole DataFrame otherwise.
    """
    prob = pf.build_problem(scored, n=pool_n, budget_fraction=budget_fraction,
                            fairness_lambda=lam, risk_gamma=gamma, seed=seed)
    s = solvers.solve_qaoa(prob, reps=reps)
    return {"x": s.x, "objective": s.objective, "seconds": s.seconds,
            "feasible": s.feasible, "extra": s.extra, "name": s.name}


# Pre-warm the DEFAULT configuration once per session, while the jury is still reading the
# applicant table. The first "Optimise" press is then instant instead of six seconds of
# silence. Only the defaults are warmed -- warming on every slider move would stall the UI.
if "warmed" not in st.session_state:
    with st.spinner("Warming up the quantum solver…"):
        try:
            cached_qaoa(10, 0.45, 0.0, 0, 1)
        except Exception:
            pass  # a cold first press is a far smaller problem than a broken page
    st.session_state.warmed = True

if not go:
    st.info("Set a budget on the left and press **Optimise portfolio**. "
            "The default configuration is pre-computed, so it returns instantly.")
    st.stop()

# ------------------------------------------------------------------ solve
st.subheader("2. The quantum optimiser picks the book")
st.caption(
    "QAOA searched for the highest-value set of customers that fits the capital budget. "
    "**FUND** = selected. The Exact and Greedy columns are classical solvers on the *same* "
    "problem, so you can see where they agree and disagree."
)

# Classical solvers finish in milliseconds, so show them before starting QAOA -- the jury
# sees a populated screen immediately instead of an 8-second blank spinner.
exact = solvers.solve_bruteforce(problem)
greedy = solvers.solve_greedy(problem)


with st.spinner(f"Running QAOA on {n_qubits} qubits (simulator)…"):
    try:
        _q = cached_qaoa(pool_n, budget_fraction, LAMBDA, int(seed), reps, GAMMA)
    except Exception as exc:  # never let the jury see a stack trace
        st.error(f"QAOA solve failed: {exc}. Showing classical results only.")
        st.stop()
q = solvers.Solution(_q["name"], _q["x"], _q["objective"], _q["seconds"], _q["feasible"], _q["extra"])

sel = pd.DataFrame({
    "applicant": [f"#{i}" for i in problem.ids],
    "group": problem.group,
    "sector": problem.sector,
    "capital_units": problem.units,
    "expected value (NT$)": problem.ev,
    "QAOA": np.where(q.x == 1, "FUND", "-"),
    "Exact": np.where(exact.x == 1, "FUND", "-"),
    "Greedy": np.where(greedy.x == 1, "FUND", "-"),
})
left, right = st.columns([3, 2])
with left:
    st.dataframe(sel.style.format({"expected value (NT$)": "{:,.0f}"}), width="stretch", hide_index=True)
with right:
    st.metric("Expected profit (QAOA)", f"NT${problem.ev @ q.x:,.0f}")
    st.metric("Capital deployed", f"{int(problem.units @ q.x)} / {problem.budget_units} units")
    n_sectors = len(set(problem.sector[q.x == 1])) if problem.sector is not None else 0
    st.metric("Concentration H", f"{problem.concentration(q.x):.3f}",
              help="Herfindahl index of capital across loan purposes. Lower is more "
                   "diversified; 1.0 means everything sits in one sector.",
              delta=f"{n_sectors} sectors funded", delta_color="off")
    gap = problem.parity_gap(q.x)
    st.metric("Approval-rate gap (F - M)", f"{gap:+.1%}",
              delta=None if not fairness_on else "fairness penalty active")
    if problem.risk_gamma > 0:
        flat = pf.build_problem(scored, n=pool_n, budget_fraction=budget_fraction,
                                fairness_lambda=LAMBDA, risk_gamma=0.0, seed=int(seed))
        fb = solvers.solve_bruteforce(flat)
        st.caption(
            f"Without diversification the optimum earns {flat.ev @ fb.x:,.0f} DM at "
            f"H={flat.concentration(fb.x):.3f}. Diversifying costs "
            f"{(flat.ev @ fb.x) - (problem.ev @ q.x):,.0f} NT$."
        )
    if problem.fairness_lambda > 0:
        base = pf.build_problem(scored, n=pool_n, budget_fraction=budget_fraction,
                                fairness_lambda=0.0, risk_gamma=GAMMA, seed=int(seed))
        b = solvers.solve_bruteforce(base)
        st.caption(
            f"Unconstrained optimum would earn {base.ev @ b.x:,.0f} DM at a "
            f"{base.parity_gap(b.x):+.1%} gap. Fairness costs "
            f"{(base.ev @ b.x) - (problem.ev @ q.x):,.0f} NT$."
        )

# ------------------------------------------------------------------ visuals
QCOL, GREY, ACC = "#4c6ef5", "#c9ccd6", "#e8833a"


def _bare(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)


@st.cache_data(show_spinner=False)
def budget_sweep(pool_n: int, lam: float, seed: int, gamma: float = 0.0):
    """Optimal profit at every budget level, by exact enumeration.

    Cheap enough to compute live (2^n per budget, n <= 12) and it shows the optimiser
    working across the whole range rather than at one arbitrary setting.
    """
    fracs = np.arange(0.15, 0.95, 0.05)
    out = []
    for f in fracs:
        pr = pf.build_problem(scored, n=pool_n, budget_fraction=float(f),
                              fairness_lambda=lam, risk_gamma=gamma, seed=seed)
        x = solvers.solve_bruteforce(pr).x
        out.append((pr.budget_units, float(pr.ev @ x), int(x.sum())))
    # Several fractions can round to the same integer budget; keep the best per budget.
    best: dict[int, tuple[float, int]] = {}
    for b, profit, n in out:
        if b not in best or profit > best[b][0]:
            best[b] = (profit, n)
    b = sorted(best)
    return b, [best[k][0] for k in b], [best[k][1] for k in b]


st.subheader("3. What the optimiser actually did")
st.caption(
    "Left: who got funded and who did not, by size of their exposure. "
    "Right: the profit achievable at **every** budget level — the orange dot is where you "
    "are now. Drag the budget slider and watch it move along the curve."
)
vcol1, vcol2 = st.columns(2)

with vcol1:
    order = np.argsort(problem.ev)
    labels = [f"#{problem.ids[i]}" for i in order]
    vals = problem.units[order]
    funded = q.x[order] == 1
    fig, ax = plt.subplots(figsize=(5.2, 3.4), dpi=140)
    ax.barh(range(len(vals)), vals,
            color=[QCOL if f else GREY for f in funded],
            edgecolor="none")
    for i, (u, f, ev) in enumerate(zip(vals, funded, problem.ev[order])):
        ax.text(u + 0.08, i, f"{ev:,.0f}", va="center", fontsize=7,
                color="#1a1a1a" if f else "#8a8a94")
    ax.set_yticks(range(len(vals)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Capital units requested")
    ax.set_xlim(0, max(vals) * 1.55)
    ax.set_title(f"Funded (blue) vs declined (grey)\n"
                 f"{int(problem.units @ q.x)} of {problem.budget_units} units deployed",
                 fontsize=9, loc="left")
    _bare(ax)
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)

with vcol2:
    bs, profits, counts = budget_sweep(pool_n, LAMBDA, int(seed), GAMMA)
    fig, ax = plt.subplots(figsize=(5.2, 3.4), dpi=140)
    ax.plot(bs, profits, "o-", color=QCOL, linewidth=2, markersize=4, zorder=3)
    here = problem.ev @ q.x
    ax.scatter([problem.budget_units], [here], s=140, color=ACC, zorder=5,
               edgecolor="white", linewidth=1.5, label="Your current budget")
    ax.set_xlabel("Capital budget (units)")
    ax.set_ylabel("Expected profit (NT$)")
    ax.set_title("Profit against every possible budget\n"
                 "Drag the budget slider and watch the dot move",
                 fontsize=9, loc="left")
    ax.legend(fontsize=8, frameon=False, loc="lower right")
    _bare(ax)
    ax.grid(axis="y", alpha=0.25, linewidth=0.6)
    fig.tight_layout()
    st.pyplot(fig, width="stretch")
    plt.close(fig)
    st.caption(
        "Diminishing returns are visible: past a point, extra capital buys progressively "
        "less profit because the remaining applicants carry worse risk-adjusted value."
    )

# ------------------------------------------------------------------ comparison
st.subheader("4. Quantum vs classical — the honest comparison")
st.caption(
    "All three solvers attack the **identical** problem. *Approximation ratio* is how close "
    "each got to the true best answer (1.0000 = perfect). *Wall clock* is how long it took. "
    "Read both columns together — that is the whole story."
)
cmp = pd.DataFrame([
    {"solver": s.name, "objective": s.objective, "approx ratio": s.objective / exact.objective,
     "wall clock (s)": s.seconds, "feasible": s.feasible}
    for s in (exact, greedy, q)
])
ccol, bcol = st.columns([3, 2])
with ccol:
    st.dataframe(
        cmp.style.format({"objective": "{:,.2f}", "approx ratio": "{:.4f}", "wall clock (s)": "{:.3f}"}),
        width="stretch", hide_index=True,
    )
with bcol:
    # st.bar_chart has no log scale, and the runtimes span four orders of magnitude, so the
    # two classical bars really are invisible slivers next to QAOA. That IS the point of the
    # chart -- but say so in the caption rather than letting it read as a rendering bug.
    st.bar_chart(cmp.set_index("solver")[["wall clock (s)"]], height=180, width="stretch")
    st.caption("Wall clock per solve — note the classical bars are not missing, they are ~0.02 s and ~0.0001 s.")

if q.objective >= exact.objective - 1e-6:
    st.success("QAOA reached the exact optimum on this instance.")
else:
    st.warning(f"QAOA landed {100 * (1 - q.objective / exact.objective):.2f}% short of the optimum.")
st.caption(
    "Classical exact search is orders of magnitude faster at this size and always optimal. "
    "We are demonstrating the mapping and measuring where it breaks, not claiming advantage at 14 qubits."
)

export = sel.copy()
export.insert(0, "instance_seed", int(seed))
export["budget_units"] = problem.budget_units
export["fairness_lambda"] = problem.fairness_lambda
st.download_button(
    "Download this portfolio (CSV)",
    export.to_csv(index=False).encode(),
    file_name=f"portfolio_seed{int(seed)}_budget{problem.budget_units}.csv",
    mime="text/csv",
)

# ------------------------------------------------------------------ show your work
st.subheader("5. Under the hood — the actual quantum circuit")
st.caption(
    "Proof that a real quantum algorithm ran, not a simulation of one in name only. "
    "The Hamiltonian is the energy landscape whose lowest point is the answer; the circuit "
    "is what searches it; the distribution is what measurement returned."
)
tabs = st.tabs(["The circuit", "Cost Hamiltonian", "Alternative portfolios"])
with tabs[0]:
    stats = solvers.ansatz_stats(problem, reps=reps)
    a, b, c, d = st.columns(4)
    a.metric("Qubits", stats["qubits"])
    b.metric("Variational parameters", stats["parameters"])
    c.metric("Transpiled depth", stats["depth"])
    d.metric("Two-qubit gates", stats["two_qubit_gates"])
    st.caption(
        f"The cost Hamiltonian has **{stats['pauli_terms']} Pauli terms**. The ansatz is "
        f"{stats['reps']} QAOA layer(s) — a cost layer exp(-i·γ·H_C) and a mixer layer "
        f"exp(-i·β·H_B) — transpiled to the simulator's basis gates. Two-qubit gate count is "
        "the figure of merit that would decide whether this is runnable on real hardware."
    )
    st.json(stats["gate_counts"], expanded=False)
with tabs[1]:
    terms, offset, nq = solvers.hamiltonian_terms(problem)
    st.write(f"Ising Hamiltonian on **{nq} qubits**, constant offset `{offset:,.2f}`. Largest terms:")
    st.dataframe(pd.DataFrame(terms).style.format({"coeff": "{:,.3f}"}),
                 width="stretch", hide_index=True)
    st.caption(
        "ZZ terms are genuine couplings between applicants. Single-Z terms come from expected value "
        "and the budget penalty; the fairness penalty adds ZZ couplings between applicants of "
        "opposite groups — which is what makes this objective quadratic rather than a plain "
        "linear knapsack."
    )
with tabs[2]:
    alts = q.extra.get("alternatives", [])
    if alts:
        st.write("QAOA returns a **distribution**, not a point solution. Top feasible portfolios by measurement probability:")
        st.dataframe(
            pd.DataFrame([
                {"portfolio": "".join(str(b) for b in a["x"]),
                 "objective": a["objective"], "probability": a["probability"]} for a in alts
            ]).style.format({"objective": "{:,.2f}", "probability": "{:.3%}"}),
            width="stretch", hide_index=True,
        )
        st.caption(
            "Under an uncertain default forecast, a ranked set of near-optimal feasible portfolios "
            "is arguably more useful than a single MILP optimum computed for probabilities that are "
            "themselves estimates. This falls out of the measurement counts at no extra cost."
        )
    else:
        st.write("No feasible alternatives recorded in the sampled distribution.")
