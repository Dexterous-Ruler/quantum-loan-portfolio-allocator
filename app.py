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
    "AI predicts default risk per applicant -> those probabilities set the coefficients of a "
    "QUBO -> QAOA allocates a fixed capital budget across the loan book. "
    "The AI and quantum modules run in **series**, not side by side."
)

scored = load_scored()
metrics = load_ai_metrics()

# ------------------------------------------------------------------ controls
with st.sidebar:
    st.header("Controls")
    pool_n = st.select_slider("Applicants in pool", options=[6, 8, 10, 12], value=10,
                              help="Drives qubit count: 6->10, 8->12, 10->14, 12->16 qubits.")
    budget_fraction = st.slider("Capital budget (fraction of total requested)", 0.20, 0.90, 0.45, 0.05)
    # Default p=1. Across repeated QAOA seeds the depths are statistically indistinguishable
    # -- the apparent "best depth" flipped between benchmark runs -- so we take the cheapest
    # one rather than pretending a winner exists. See DELIVERABLE_4.md, table A.
    reps = st.select_slider("QAOA depth p", options=[1, 2, 3], value=1)
    fairness_on = st.toggle("Apply fairness penalty", value=False,
                            help="Penalises approval-rate disparity between groups. Adds zero qubits.")
    fairness_lambda = st.slider("Fairness weight lambda", 0, 40000, 8000, 1000,
                                disabled=not fairness_on)
    seed = st.number_input("Instance seed", 0, 999, 0, 1)
    go = st.button("Optimise portfolio", type="primary", width="stretch")

problem = pf.build_problem(
    scored, n=pool_n, budget_fraction=budget_fraction,
    fairness_lambda=float(fairness_lambda) if fairness_on else 0.0, seed=int(seed),
)
_, n_qubits = pf.qubo_and_qubits(problem)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Applicants", problem.n)
c2.metric("Capital budget", f"{problem.budget_units} units")
c3.metric("Qubits", n_qubits)
c4.metric("AI model AUC", f"{metrics['gbm_auc']:.3f}")

# ------------------------------------------------------------------ applicants
st.subheader("1. AI model output — risk-adjusted value per applicant")
view = problem.meta[["credit_amount", "duration_months", "age_years", "sex", "p_default", "expected_value"]].copy()
view.insert(0, "applicant", [f"#{i}" for i in problem.ids])
view["capital_units"] = problem.units
view = view.rename(columns={"p_default": "P(default)", "expected_value": "expected value (DM)"})
st.dataframe(
    view.style.format({"P(default)": "{:.1%}", "expected value (DM)": "{:,.0f}", "credit_amount": "{:,.0f}"})
        .background_gradient(subset=["P(default)"], cmap="Reds"),
    width="stretch", hide_index=True,
)

@st.cache_data(show_spinner=False)
def cached_qaoa(pool_n: int, budget_fraction: float, lam: float, seed: int, reps: int):
    """Cache by the control values, so re-showing a configuration during a demo is instant.

    Rebuilds the problem inside rather than taking it as an argument: Streamlit would have to
    hash the whole DataFrame otherwise.
    """
    prob = pf.build_problem(scored, n=pool_n, budget_fraction=budget_fraction,
                            fairness_lambda=lam, seed=seed)
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
st.subheader("2. Allocation under the capital budget")

# Classical solvers finish in milliseconds, so show them before starting QAOA -- the jury
# sees a populated screen immediately instead of an 8-second blank spinner.
exact = solvers.solve_bruteforce(problem)
greedy = solvers.solve_greedy(problem)


with st.spinner(f"Running QAOA on {n_qubits} qubits (simulator)…"):
    try:
        _q = cached_qaoa(pool_n, budget_fraction,
                         float(fairness_lambda) if fairness_on else 0.0, int(seed), reps)
    except Exception as exc:  # never let the jury see a stack trace
        st.error(f"QAOA solve failed: {exc}. Showing classical results only.")
        st.stop()
q = solvers.Solution(_q["name"], _q["x"], _q["objective"], _q["seconds"], _q["feasible"], _q["extra"])

sel = pd.DataFrame({
    "applicant": [f"#{i}" for i in problem.ids],
    "sex": problem.sex,
    "capital_units": problem.units,
    "expected value (DM)": problem.ev,
    "QAOA": np.where(q.x == 1, "FUND", "-"),
    "Exact": np.where(exact.x == 1, "FUND", "-"),
    "Greedy": np.where(greedy.x == 1, "FUND", "-"),
})
left, right = st.columns([3, 2])
with left:
    st.dataframe(sel.style.format({"expected value (DM)": "{:,.0f}"}), width="stretch", hide_index=True)
with right:
    st.metric("Expected profit (QAOA)", f"{problem.ev @ q.x:,.0f} DM")
    st.metric("Capital deployed", f"{int(problem.units @ q.x)} / {problem.budget_units} units")
    gap = problem.parity_gap(q.x)
    st.metric("Approval-rate gap (F - M)", f"{gap:+.1%}",
              delta=None if not fairness_on else "fairness penalty active")
    if problem.fairness_lambda > 0:
        base = pf.build_problem(scored, n=pool_n, budget_fraction=budget_fraction,
                                fairness_lambda=0.0, seed=int(seed))
        b = solvers.solve_bruteforce(base)
        st.caption(
            f"Unconstrained optimum would earn {base.ev @ b.x:,.0f} DM at a "
            f"{base.parity_gap(b.x):+.1%} gap. Fairness costs "
            f"{(base.ev @ b.x) - (problem.ev @ q.x):,.0f} DM."
        )

# ------------------------------------------------------------------ visuals
QCOL, GREY, ACC = "#4c6ef5", "#c9ccd6", "#e8833a"


def _bare(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.grid(axis="x", alpha=0.25, linewidth=0.6)
    ax.set_axisbelow(True)


@st.cache_data(show_spinner=False)
def budget_sweep(pool_n: int, lam: float, seed: int):
    """Optimal profit at every budget level, by exact enumeration.

    Cheap enough to compute live (2^n per budget, n <= 12) and it shows the optimiser
    working across the whole range rather than at one arbitrary setting.
    """
    fracs = np.arange(0.15, 0.95, 0.05)
    out = []
    for f in fracs:
        pr = pf.build_problem(scored, n=pool_n, budget_fraction=float(f),
                              fairness_lambda=lam, seed=seed)
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
        ax.text(u + 0.08, i, f"{ev:,.0f} DM", va="center", fontsize=7,
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
    bs, profits, counts = budget_sweep(pool_n, problem.fairness_lambda, int(seed))
    fig, ax = plt.subplots(figsize=(5.2, 3.4), dpi=140)
    ax.plot(bs, profits, "o-", color=QCOL, linewidth=2, markersize=4, zorder=3)
    here = problem.ev @ q.x
    ax.scatter([problem.budget_units], [here], s=140, color=ACC, zorder=5,
               edgecolor="white", linewidth=1.5, label="Your current budget")
    ax.set_xlabel("Capital budget (units)")
    ax.set_ylabel("Expected profit (DM)")
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
st.subheader("4. Quantum vs classical — same QUBO, same instance")
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
st.subheader("5. What the quantum module is actually doing")
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
