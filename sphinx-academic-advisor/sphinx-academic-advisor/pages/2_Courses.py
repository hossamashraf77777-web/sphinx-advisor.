"""Courses catalog: search, filter and inspect courses."""

import pandas as pd
import streamlit as st

from agent import eligibility, rules
from ui import components as ui
from ui.session import start_page

ds = start_page("Courses Catalog", "Search the curriculum and see how each course relates to your record.")
ctx = rules.build_context(ds)


def student_status(code: str) -> str:
    if code not in ctx.attempted:
        return "Not taken"
    if ctx.passed is None:
        return "Unverified"
    return "Passed" if code in ctx.passed else "Failed attempt"


all_courses = list(ds.courses.values())
col_search, col_category, col_level = st.columns([2, 1, 1])
query = col_search.text_input("Search by code or title", placeholder="For example: a course code or a word from the title")
categories = col_category.multiselect("Category", sorted({c.category for c in all_courses}))
levels = col_level.multiselect("Level", sorted({c.level for c in all_courses}))

filtered = [
    c
    for c in all_courses
    if (not query or query.strip().lower() in f"{c.code} {c.title}".lower())
    and (not categories or c.category in categories)
    and (not levels or c.level in levels)
]

if not filtered:
    ui.empty_state("No courses match", "Try a shorter search or clear the filters.")
    st.stop()

table = pd.DataFrame(
    [
        {
            "Code": c.code,
            "Title": c.title,
            "Credits": c.credits,
            "Category": c.category,
            "Level": c.level,
            "Prerequisites": ("Unknown" if not c.prerequisites_known else ", ".join(c.prerequisites) or "None"),
            "Your status": student_status(c.code),
        }
        for c in filtered
    ]
)
st.caption(f"Showing {len(filtered)} of {len(all_courses)} courses.")
st.dataframe(table, hide_index=True)
st.download_button("Download this list (CSV)", table.to_csv(index=False).encode("utf-8"), "courses.csv", "text/csv")

st.markdown("## Course details")
code = st.selectbox(
    "Choose a course",
    [c.code for c in filtered],
    format_func=lambda value: f"{value} - {ds.courses[value].title}",
)
course = ds.courses[code]
ui.facts(
    [
        ("Credit hours", f"{course.credits:g}"),
        ("Category", course.category),
        ("Level", course.level),
        ("Your status", student_status(code)),
    ]
)
if course.description:
    st.write(course.description)

st.markdown("**Prerequisites**")
if not course.prerequisites_known:
    ui.notice("warning", "Prerequisites unknown", "The curriculum data does not say what the prerequisites are.")
elif not course.prerequisites:
    st.write("None listed.")
else:
    for prereq in course.prerequisites:
        if ctx.passed is None:
            tag = ui.badge("Unverified", "warning")
        else:
            tag = ui.badge("Passed", "success") if prereq in ctx.passed else ui.badge("Not passed", "danger")
        st.markdown(f"{rules.label(ctx, prereq)} &nbsp; {tag}", unsafe_allow_html=True)

required_by = [c for c in all_courses if code in c.prerequisites]
st.markdown("**Required by**")
st.write(", ".join(rules.label(ctx, c.code) for c in required_by) if required_by else "No other course lists it as a prerequisite.")

st.markdown("**Eligibility for you**")
evaluation = eligibility.evaluate_course(course, ctx)
st.markdown(ui.status_badge(evaluation.status, course_level=True), unsafe_allow_html=True)
for decision in evaluation.decisions:
    ui.decision_card(decision)
