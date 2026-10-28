"""Graduation planner: remaining requirements and a proposed path."""

import pandas as pd
import streamlit as st

from agent import graduation
from ui import components as ui
from ui.session import start_page

ds = start_page("Graduation Planner", "What is left to graduate, and one possible path to get there.")
progress = graduation.compute_progress(ds)

if not progress.verified:
    ui.notice(
        "warning",
        "Graduation requirements cannot be verified",
        "Missing: " + "; ".join(progress.missing_rules) + ". Provide them in the regulations file.",
    )
    st.stop()

cols = st.columns(3)
cols[0].metric("Credits earned", f"{progress.credits_earned:g}")
cols[1].metric("Credits required", f"{progress.total_required:g}")
cols[2].metric("Credits remaining", f"{progress.remaining_credits:g}")
st.progress(progress.percent_complete or 0.0, text=f"{(progress.percent_complete or 0) * 100:.0f}% of required credits earned")

st.markdown("## Requirements by category")
st.dataframe(pd.DataFrame(progress.category_rows), hide_index=True)

st.markdown("## Remaining mandatory courses")
if not progress.remaining_mandatory:
    ui.empty_state("None remaining", "Every mandatory course has been passed.")
else:
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Code": c.code,
                    "Title": c.title,
                    "Credits": c.credits,
                    "Prerequisites": "Unknown" if not c.prerequisites_known else ", ".join(c.prerequisites) or "None",
                }
                for c in progress.remaining_mandatory
            ]
        ),
        hide_index=True,
    )

st.markdown("## Proposed path")
limit = st.number_input(
    "Your planning credit load per term (0 = not set)",
    min_value=0,
    max_value=40,
    value=0,
    step=1,
    help="Your own planning value. An official limit from the regulations file is used instead when provided.",
)
plan = graduation.build_plan(ds, limit or None)

for message in plan.messages:
    ui.notice("warning", "Planning note", message)

if plan.terms:
    if plan.complete:
        ui.notice("success", "Path found", f"{len(plan.terms)} term(s) are enough to finish the listed requirements under the assumptions below.")
    rows = []
    for term in plan.terms:
        for course in term.courses:
            rows.append({"Planned term": f"Term {term.number}", "Code": course.code, "Title": course.title, "Credits": course.credits})
    plan_table = pd.DataFrame(rows)
    for term in plan.terms:
        with st.expander(f"Term {term.number} - {term.credits:g} credits", expanded=term.number == 1):
            st.dataframe(plan_table[plan_table["Planned term"] == f"Term {term.number}"], hide_index=True)
    st.download_button("Download plan (CSV)", plan_table.to_csv(index=False).encode("utf-8"), "graduation_plan.csv", "text/csv")

if plan.unscheduled:
    st.markdown("**Courses that could not be scheduled**")
    for course, reason in plan.unscheduled:
        ui.notice("danger", f"{course.code} - {course.title}", reason)

if plan.assumptions:
    with st.expander("Assumptions behind this plan"):
        for assumption in plan.assumptions:
            st.write(f"- {assumption}")
