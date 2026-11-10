"""Schedule (or edit) an interview. Saved as 'pending'; the inbox agent adds it to Google Calendar."""

from datetime import date, datetime, time, timedelta

import streamlit as st

from jobdash import db
from jobdash.constants import INTERVIEW_KINDS
from jobdash.times import local_to_utc, to_local
from jobdash.ui import app_options, none_if_blank

apps = db.applications()
options = app_options(apps)

edit_id = st.session_state.get("edit_interview")
current = None
if edit_id is not None:
    found = db.interviews()
    found = found[found["id"] == edit_id] if not found.empty else found
    current = found.iloc[0].to_dict() if not found.empty else None

st.title("Edit interview" if current else "Schedule interview")

if not options:
    st.info("Add an application first (Applications page), then schedule its interview.")
    st.stop()

if current:
    if st.button("Schedule a new one instead", icon=":material/add:"):
        st.session_state.pop("edit_interview", None)
        st.rerun()

start_local = to_local(current["starts_at"]) if current else None
end_local = to_local(current["ends_at"]) if current else None
default_minutes = int((end_local - start_local).total_seconds() // 60) if current else 60
ids = list(options.keys())

with st.form("interview_form", clear_on_submit=current is None):
    application_id = st.selectbox(
        "Application",
        ids,
        index=ids.index(int(current["application_id"])) if current and int(current["application_id"]) in ids else None,
        format_func=lambda k: options[k],
        placeholder="Search company or role",
    )
    c1, c2, c3, c4 = st.columns(4)
    kind_options = INTERVIEW_KINDS
    kind = c1.selectbox(
        "Kind",
        kind_options,
        index=kind_options.index(current["kind"]) if current and current.get("kind") in kind_options else 0,
    )
    day = c2.date_input("Date (Central)", value=start_local.date() if current else date.today() + timedelta(days=1))
    start = c3.time_input("Start", value=start_local.time() if current else time(10, 0), step=timedelta(minutes=15))
    minutes = c4.number_input("Length (min)", min_value=15, max_value=480, step=15, value=default_minutes)
    location = st.text_input(
        "Location or video link", value=(current or {}).get("location") or "", placeholder="https://zoom.us/j/… or address"
    )
    interviewers = st.text_input("Interviewers", value=(current or {}).get("interviewers") or "")
    notes = st.text_area("Notes / prep", value=(current or {}).get("notes") or "", height=100)
    submitted = st.form_submit_button("Save interview", type="primary")

if submitted:
    if application_id is None:
        st.error("Pick the application this interview is for.")
        st.stop()
    starts_at = local_to_utc(day, start)
    values = {
        "application_id": application_id,
        "kind": kind,
        "starts_at": starts_at,
        "ends_at": starts_at + timedelta(minutes=int(minutes)),
        "location": none_if_blank(location),
        "interviewers": none_if_blank(interviewers),
        "notes": none_if_blank(notes),
    }
    if starts_at < datetime.now(starts_at.tzinfo) - timedelta(days=1):
        st.warning("That date is in the past. Saved anyway, in case you're logging a past interview.")
    try:
        db.save_interview(values, interview_id=int(edit_id) if current else None)
        st.session_state.pop("edit_interview", None)
        st.success(
            "Saved. It shows on the Calendar page now and will be added to Google Calendar on the next inbox run."
        )
    except Exception as err:  # noqa: BLE001
        st.error(f"Could not save: {err}")

st.caption(
    "Times are Central. The inbox agent creates the Google Calendar event (with 1-day and 1-hour reminders) "
    "on its next run, every 2 hours between 7am and 9pm."
)
