"""Job Dashboard: Streamlit entry point.  Run with:  streamlit run app.py"""

import streamlit as st

from jobdash import auth, db
from jobdash.times import fmt

st.set_page_config(page_title="Job Dashboard", page_icon="💼", layout="wide")

# Fail early, with a readable message, if the database isn't reachable.
try:
    db.conn()
except db.ConfigError as err:
    st.error(str(err))
    st.stop()
except Exception as err:  # noqa: BLE001
    st.error(f"Could not connect to the database: {err}")
    st.info("Check DATABASE_URL in your .env file (see README.md).")
    st.stop()

# Sign-in gate: nothing below runs until you're signed in.
try:
    signed_in_as = auth.require_login()
except auth.AuthConfigError as err:
    st.error(str(err))
    st.stop()

pages = [
    st.Page("views/pipeline.py", title="Pipeline", icon=":material/dashboard:", default=True),
    st.Page("views/applications.py", title="Applications", icon=":material/work:"),
    st.Page("views/calendar_view.py", title="Calendar", icon=":material/calendar_month:"),
    st.Page("views/schedule.py", title="Schedule interview", icon=":material/event_available:"),
    st.Page("views/review.py", title="Review", icon=":material/rule:"),
]
nav = st.navigation(pages)

with st.sidebar:
    run = db.last_run()
    if run:
        st.caption(f"Inbox last checked {fmt(run['finished_at'])}")
        if run.get("errors"):
            st.caption(f":red[Last run had errors:] {run['errors']}")
    else:
        st.caption("The inbox agent hasn't finished a run yet.")
    if st.button("Refresh data", icon=":material/refresh:", use_container_width=True):
        st.cache_data.clear()
        st.rerun()
    st.divider()
    st.caption(f"Signed in as {signed_in_as}")
    if st.button("Sign out", icon=":material/logout:", use_container_width=True):
        auth.sign_out()

nav.run()
