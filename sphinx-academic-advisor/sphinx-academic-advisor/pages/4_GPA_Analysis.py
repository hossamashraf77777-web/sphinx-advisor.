"""GPA analysis: term and cumulative GPA, grade distribution and a what-if calculator."""

import pandas as pd
import streamlit as st

import config
from services import gpa_calculator as gpa
from ui import components as ui
from ui.session import start_page

ds = start_page("GPA Analysis", "How your GPA developed, and what future grades could do to it.")
student, regs, courses = ds.student, ds.regulations, ds.courses

if not student.records:
    ui.empty_state("No grades yet", "GPA analysis needs at least one graded course.")
    st.stop()

try:
    summary = gpa.calculate_gpa(student.records, courses, regs)
    terms = gpa.term_summaries(student.records, courses, regs)
except gpa.MissingRuleError as exc:
    ui.notice("warning", "GPA cannot be calculated", f"{exc} Add it to the regulations file.")
    st.stop()

cols = st.columns(3)
cols[0].metric("Cumulative GPA", ui.format_gpa(summary.gpa))
cols[1].metric("Quality points", f"{summary.quality_points:.1f}")
cols[2].metric("Credits attempted", f"{summary.credits_attempted:g}")
if not summary.retake_policy_verified:
    ui.notice("warning", "Retake policy missing", "A course was repeated, so the GPA may not follow the official policy.")

st.markdown("## GPA by term")
trend = pd.DataFrame(
    {
        "Term GPA": [round(t.term_gpa, 2) if t.term_gpa is not None else None for t in terms],
        "Cumulative GPA": [round(t.cumulative_gpa, 2) if t.cumulative_gpa is not None else None for t in terms],
    },
    index=[t.term for t in terms],
)
if len(terms) < 2:
    st.caption("Only one term is recorded, so there is no trend to show yet.")
st.line_chart(trend, color=config.CHART_COLORS[:2])
st.dataframe(trend.reset_index(names="Term"), hide_index=True)

st.markdown("## Grade distribution")
distribution = gpa.grade_distribution(student.records)
ordered = sorted(distribution, key=lambda g: -(regs.grade_scale.get(g, -1)))
st.bar_chart(pd.Series([distribution[g] for g in ordered], index=ordered, name="Courses"), color=config.CHART_COLORS[0])

st.markdown("## What-if calculator")
st.caption("Hypothetical only: pick courses and expected grades to see the projected cumulative GPA. Nothing is saved.")
passed = gpa.passed_codes(student.records, regs) if regs.min_passing_points is not None else set()
options = [code for code in courses if code not in passed]
with st.form("what_if"):
    chosen = st.multiselect(
        "Courses you plan to take (or retake)",
        options,
        format_func=lambda c: f"{c} - {courses[c].title} ({courses[c].credits:g} cr)",
    )
    grade_choices = sorted(regs.grade_scale, key=lambda g: -regs.grade_scale[g])
    expected = st.selectbox("Expected grade for all selected courses", grade_choices)
    submitted = st.form_submit_button("Calculate projected GPA", type="primary")

if submitted:
    if not chosen:
        st.warning("Select at least one course first.")
    else:
        projected = gpa.project_gpa(student.records, [(c, expected) for c in chosen], courses, regs)
        change = (projected.gpa - summary.gpa) if projected.gpa is not None and summary.gpa is not None else None
        out = st.columns(2)
        out[0].metric("Projected cumulative GPA", ui.format_gpa(projected.gpa), f"{change:+.2f}" if change is not None else None)
        out[1].metric("Added credits", f"{sum(courses[c].credits for c in chosen):g}")
