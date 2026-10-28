"""Smart Academic Advisor: a rule-based agent that shows every decision and why."""

import pandas as pd
import streamlit as st

from agent import advisor, eligibility, rules
from ui import components as ui
from ui.session import start_page

ds = start_page("Smart Academic Advisor", "A rule-based agent: it checks the rules and explains each result.")
st.caption(
    "This advisor follows written rules only. It does not use machine learning or a language model, "
    "and it says 'needs verification' whenever a rule or a piece of data is missing."
)

tab_standing, tab_course, tab_rules = st.tabs(["Academic standing", "Check a course", "Rules in use"])

with tab_standing:
    cgpa = advisor.current_cgpa(ds)
    st.metric("Cumulative GPA", ui.format_gpa(cgpa))
    ui.decision_card(advisor.evaluate_standing(ds))
    st.markdown("## Everything that needs attention")
    alerts = advisor.build_alerts(ds)
    if not alerts:
        ui.empty_state("Nothing to report", "No alerts were found.")
    for alert in alerts:
        ui.notice(alert.level, alert.title, alert.message)
    report = advisor.build_report(ds)
    st.download_button("Download advising summary (text)", report.encode("utf-8"), "advising_summary.txt", "text/plain")

with tab_course:
    ctx = rules.build_context(ds)
    code = st.selectbox(
        "Which course do you want to check?",
        list(ds.courses),
        format_func=lambda value: f"{value} - {ds.courses[value].title}",
    )
    evaluation = eligibility.evaluate_course(ds.courses[code], ctx)
    st.markdown(f"**Verdict:** {ui.status_badge(evaluation.status, course_level=True)}", unsafe_allow_html=True)
    st.write(evaluation.summary)
    st.markdown("## Rule by rule")
    for decision in evaluation.decisions:
        ui.decision_card(decision)

with tab_rules:
    st.write("These are the regulation values the agent is using. 'No' means the rule is missing, so any decision that needs it is marked 'needs verification'.")
    st.dataframe(pd.DataFrame(advisor.rules_in_use(ds.regulations)), hide_index=True)
    st.caption(f"Source: {ds.regulations.label or ds.source_dir}")
