"""Semester recommendations: eligible courses for next term, with the reason for each."""

import pandas as pd
import streamlit as st

from agent import recommendations
from ui import components as ui
from ui.session import start_page

ds = start_page("Semester Recommendations", "Courses you can take next semester, and why.")

budget = st.number_input(
    "Your planning credit load (0 = not set)",
    min_value=0,
    max_value=40,
    value=0,
    step=1,
    help="This is your own planning value. If the regulations file provides an official limit, that limit is used instead.",
)
result = recommendations.recommend_courses(ds, budget or None)

for decision in result.credit_decisions:
    ui.decision_card(decision)
for note in result.notes:
    ui.notice("info", "Note", note)

st.markdown("## Recommended courses")
if not result.recommended:
    ui.empty_state("Nothing to recommend", "No eligible course was found for the current record and rules.")
else:
    cols = st.columns(2)
    cols[0].metric("Courses", len(result.recommended))
    cols[1].metric("Total credits", f"{result.total_credits:g}")
    table = pd.DataFrame(
        [
            {
                "Code": r.course.code,
                "Title": r.course.title,
                "Credits": r.course.credits,
                "Priority": {0: "Retake", 1: "Mandatory", 2: "Needed credits"}.get(r.tier, "Other"),
                "Check": "Eligible" if r.evaluation.status.value == "passed" else "Needs verification",
                "Why": r.reason,
            }
            for r in result.recommended
        ]
    )
    st.dataframe(table, hide_index=True)
    st.download_button("Download recommendations (CSV)", table.to_csv(index=False).encode("utf-8"), "recommendations.csv", "text/csv")
    st.markdown("**Rule checks per course**")
    for rec in result.recommended:
        with st.expander(f"{rec.course.code} - {rec.course.title}"):
            st.write(rec.reason)
            for decision in rec.evaluation.decisions:
                ui.decision_card(decision)

if result.deferred:
    st.markdown("## Eligible but not selected")
    st.dataframe(
        pd.DataFrame([{"Code": r.course.code, "Title": r.course.title, "Credits": r.course.credits, "Why": r.reason} for r in result.deferred]),
        hide_index=True,
    )

if result.rejected:
    st.markdown("## Not eligible yet")
    for evaluation in result.rejected:
        with st.expander(f"{evaluation.course.code} - {evaluation.course.title}"):
            for decision in evaluation.decisions:
                ui.decision_card(decision)
