"""Streamlit interface for the warehouse-space leasing optimizer."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from lease_solver import solve_lease_problem


DEFAULT_DEMAND = [30_000, 20_000, 40_000, 10_000, 50_000]
DEFAULT_COSTS = [65, 100, 135, 160, 190]


def money(value: float) -> str:
    """Format a number as a whole-dollar amount."""

    return f"${value:,.0f}"


st.set_page_config(
    page_title="Warehouse Lease Optimizer",
    page_icon="📦",
    layout="wide",
)

st.title("📦 Warehouse Lease Optimizer")
st.write(
    "Find the lowest-cost combination of warehouse leases that covers the "
    "required square footage in every month."
)

with st.sidebar:
    st.header("Problem inputs")
    month_count = st.number_input(
        "Number of months",
        min_value=1,
        max_value=12,
        value=5,
        step=1,
        help="The app creates lease choices for every start month and duration.",
    )

    st.subheader("Required space")
    demand: list[float] = []
    for month in range(1, int(month_count) + 1):
        default = DEFAULT_DEMAND[month - 1] if month <= len(DEFAULT_DEMAND) else 0
        demand.append(
            st.number_input(
                f"Month {month} (sq. ft.)",
                min_value=0.0,
                value=float(default),
                step=1_000.0,
                key=f"demand_{month}",
            )
        )

    st.subheader("Lease cost by duration")
    costs: list[float] = []
    for duration in range(1, int(month_count) + 1):
        default = (
            DEFAULT_COSTS[duration - 1]
            if duration <= len(DEFAULT_COSTS)
            else DEFAULT_COSTS[-1]
        )
        costs.append(
            st.number_input(
                f"{duration}-month lease ($/sq. ft.)",
                min_value=0.0,
                value=float(default),
                step=1.0,
                key=f"cost_{duration}",
            )
        )

    solve_button = st.button("Solve optimization", type="primary", use_container_width=True)

if solve_button:
    st.session_state["lease_result"] = solve_lease_problem(demand, costs)

result = st.session_state.get("lease_result")
if result is None:
    result = solve_lease_problem(DEFAULT_DEMAND, DEFAULT_COSTS)

total_cost = float(result["total_cost"])
plan_rows = result["plan"]
demand_values = result["demand"]
leased_values = result["leased_by_month"]

metric_1, metric_2, metric_3 = st.columns(3)
metric_1.metric("Minimum total cost", money(total_cost))
metric_2.metric("Lease decisions", str(len(plan_rows)))
metric_3.metric("Peak required space", f"{max(demand_values):,.0f} sq. ft.")

st.subheader("Recommended lease plan")
if plan_rows:
    plan_df = pd.DataFrame(plan_rows)
    plan_df = plan_df.rename(
        columns={
            "start_month": "Start month",
            "end_month": "End month",
            "lease_length": "Length (months)",
            "square_feet": "Square feet",
            "cost_per_sq_ft": "Cost / sq. ft.",
            "lease_cost": "Lease cost",
        }
    )
    st.dataframe(
        plan_df.style.format(
            {
                "Square feet": "{:,.0f}",
                "Cost / sq. ft.": "${:,.2f}",
                "Lease cost": "${:,.0f}",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )
else:
    st.info("No space is required, so the least-cost plan has no leases.")

coverage_df = pd.DataFrame(
    {
        "Month": [f"Month {month}" for month in range(1, len(demand_values) + 1)],
        "Required space": demand_values,
        "Leased space": leased_values,
    }
)
coverage_df["Surplus space"] = (
    coverage_df["Leased space"] - coverage_df["Required space"]
)

st.subheader("Monthly coverage")
st.dataframe(
    coverage_df.style.format(
        {
            "Required space": "{:,.0f}",
            "Leased space": "{:,.0f}",
            "Surplus space": "{:,.0f}",
        }
    ),
    use_container_width=True,
    hide_index=True,
)
st.bar_chart(coverage_df.set_index("Month")[['Required space', 'Leased space']])

with st.expander("How the optimization works"):
    st.markdown(
        "Let **x(s, d)** be the square feet leased beginning in month **s** "
        "for **d** months. The app minimizes the sum of `cost[d] × x(s, d)` "
        "subject to leased space being at least the required space in each "
        "month. Lease amounts are allowed to be fractional because the input "
        "costs are linear per square foot."
    )
    st.latex(
        r"\min \sum_{s,d} c_d x_{s,d}"
        r"\qquad\text{subject to}\qquad"
        r"\sum_{(s,d)\text{ active in }m}x_{s,d}\geq R_m,\quad x_{s,d}\geq 0"
    )

st.caption(
    "Tip: change the values in the sidebar and click Solve optimization to "
    "test another leasing scenario."
)
