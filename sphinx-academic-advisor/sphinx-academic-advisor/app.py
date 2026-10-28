"""Entry point. Run with:  streamlit run app.py

It sets up the page, loads the stylesheet, defines the navigation and runs the chosen page.
To add a new page: create a file in pages/ and add one st.Page(...) line below.
"""

import streamlit as st

import config
from ui.session import render_sidebar
from ui.theme import apply_theme

st.set_page_config(page_title=config.APP_NAME, page_icon="🎓", layout="wide")
apply_theme()

navigation = st.navigation(
    {
        "Overview": [
            st.Page("pages/1_Home.py", title="Home", icon=":material/home:", default=True),
            st.Page("pages/2_Courses.py", title="Courses Catalog", icon=":material/menu_book:"),
            st.Page("pages/3_Academic_Profile.py", title="My Academic Profile", icon=":material/person:"),
        ],
        "Analysis": [
            st.Page("pages/4_GPA_Analysis.py", title="GPA Analysis", icon=":material/monitoring:"),
            st.Page("pages/5_Smart_Advisor.py", title="Smart Academic Advisor", icon=":material/psychology:"),
        ],
        "Planning": [
            st.Page("pages/6_Semester_Recommendations.py", title="Semester Recommendations", icon=":material/event_available:"),
            st.Page("pages/7_Graduation_Planner.py", title="Graduation Planner", icon=":material/school:"),
        ],
    }
)
render_sidebar()
navigation.run()
