"""Home dashboard: where the student stands right now."""

import pandas as pd
import streamlit as st

from agent import advisor, graduation
from services import gpa_calculator as gpa
from ui import components as ui
from ui.session import start_page

ds = start_page("Home", "Where you stand now: credits, GPA and what needs attention.")
regs = ds.regulations

try:
    summary = gpa.calculate_gpa(ds.student.records, ds.courses, regs)
except gpa.MissingRuleError:
    summary = None
progress = graduation.compute_progress(ds)

st.markdown(f"### {ds.student.name}")
ui.facts([("Student ID", ds.student.student_id), ("Program", ds.student.program), ("Admitted", ds.student.admission_term)])

cols = st.columns(4)
cols[0].metric("Cumulative GPA", ui.format_gpa(summary.gpa if summary else None))
cols[1].metric(
    "Credits earned",
    f"{summary.credits_earned:g}" if summary and summary.credits_earned is not None else "Not available",
)
cols[2].metric(
    "Credits to graduate",
    f"{progress.remaining_credits:g}" if progress.verified else "Not verified",
    help="Total required credits minus credits earned. Needs the graduation rules in the regulations file.",
)
passed_count = len(gpa.passed_codes(ds.student.records, regs)) if regs.min_passing_points is not None else None
cols[3].metric("Courses passed", passed_count if passed_count is not None else "Not available")
st.caption("GPA is calculated with the grade scale in the loaded regulations file.")

st.markdown("## Alerts")
alerts = advisor.build_alerts(ds)
if not alerts:
    ui.empty_state("No alerts", "All rule checks completed without problems or missing information.")
for alert in alerts:
    ui.notice(alert.level, alert.title, alert.message)

st.markdown("## Recent terms")
if summary is None or not ds.student.records:
    ui.empty_state("No term data", "There are no graded courses to summarise yet.")
else:
    rows = [
        {
            "Term": t.term,
            "Credits attempted": t.credits_attempted,
            "Credits earned": t.credits_earned,
            "Term GPA": round(t.term_gpa, 2) if t.term_gpa is not None else None,
            "Cumulative GPA": round(t.cumulative_gpa, 2) if t.cumulative_gpa is not None else None,
        }
        for t in gpa.term_summaries(ds.student.records, ds.courses, regs)
    ]
    st.dataframe(pd.DataFrame(rows), hide_index=True)

st.markdown("## Next steps")
left, middle, right = st.columns(3)
left.page_link("pages/6_Semester_Recommendations.py", label="See next-semester recommendations", icon=":material/event_available:")
middle.page_link("pages/7_Graduation_Planner.py", label="Open the graduation planner", icon=":material/school:")
right.page_link("pages/5_Smart_Advisor.py", label="Ask the advisor about a course", icon=":material/psychology:")
