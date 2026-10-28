"""Academic profile: student information and the full course history."""

import pandas as pd
import streamlit as st

from services import gpa_calculator as gpa
from ui import components as ui
from ui.session import start_page

ds = start_page("My Academic Profile", "Your details, completed courses and grades.")
student, regs = ds.student, ds.regulations

st.markdown("## Student information")
ui.facts(
    [
        ("Name", student.name),
        ("Student ID", student.student_id),
        ("Program", student.program),
        ("Admission term", student.admission_term or "Not provided"),
    ]
)

st.markdown("## Course history")
if not student.records:
    ui.empty_state("No courses on record", "This student has no recorded course attempts yet.")
    st.stop()


def result_label(grade: str) -> str:
    try:
        passing = gpa.is_passing(grade, regs)
    except gpa.MissingRuleError:
        return "Unverified"
    return {True: "Passed", False: "Failed", None: "Unknown grade"}[passing]


def points_for(grade: str):
    try:
        return gpa.grade_points(grade, regs)
    except gpa.MissingRuleError:
        return None


rows = []
for record in sorted(student.records, key=lambda r: (r.term_order, r.course_code)):
    course = ds.courses.get(record.course_code)
    rows.append(
        {
            "Term": record.term,
            "Code": record.course_code,
            "Title": course.title if course else "Unknown course",
            "Credits": course.credits if course else None,
            "Grade": record.grade,
            "Grade points": points_for(record.grade),
            "Result": result_label(record.grade),
        }
    )
history = pd.DataFrame(rows)

terms = ["All terms"] + list(dict.fromkeys(history["Term"]))
chosen = st.selectbox("Show", terms)
view = history if chosen == "All terms" else history[history["Term"] == chosen]
st.dataframe(view, hide_index=True)
st.download_button("Download history (CSV)", history.to_csv(index=False).encode("utf-8"), "academic_history.csv", "text/csv")

st.markdown("## Summary")
try:
    summary = gpa.calculate_gpa(student.records, ds.courses, regs)
except gpa.MissingRuleError as exc:
    ui.notice("warning", "Summary not available", str(exc))
else:
    cols = st.columns(3)
    cols[0].metric("Cumulative GPA", ui.format_gpa(summary.gpa))
    cols[1].metric("Credits attempted", f"{summary.credits_attempted:g}")
    cols[2].metric("Credits earned", f"{summary.credits_earned:g}" if summary.credits_earned is not None else "Not available")
    if not summary.retake_policy_verified:
        ui.notice("warning", "Repeated course", "A course appears more than once but no retake policy is provided.")
    if summary.skipped_records:
        ui.notice("warning", "Records skipped", f"{summary.skipped_records} record(s) were ignored (unknown course or grade).")
