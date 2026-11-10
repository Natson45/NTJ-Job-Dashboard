"""Calendar: month / week / list view of interviews, with details and cancel."""

from datetime import timedelta

import streamlit as st
from streamlit_calendar import calendar

from jobdash import db
from jobdash.constants import BLUE, BLUE_LIGHT, CRITICAL, TEXT_PRIMARY
from jobdash.device import is_phone
from jobdash.times import LOCAL_TZ_NAME, fmt, now_local, to_local

st.title("Calendar")

if st.button("Schedule an interview", icon=":material/add:", type="primary"):
    st.switch_page("views/schedule.py")

now = now_local()
rows = db.interviews(start=now - timedelta(days=120), end=now + timedelta(days=240))
rows = rows[rows["sync_state"] != "cancelled"] if not rows.empty else rows

STATE_STYLE = {
    "synced": {"backgroundColor": BLUE, "borderColor": BLUE, "textColor": "#ffffff"},
    "pending": {"backgroundColor": BLUE_LIGHT, "borderColor": BLUE, "textColor": TEXT_PRIMARY},
    "cancel_requested": {"backgroundColor": "#f0efec", "borderColor": CRITICAL, "textColor": TEXT_PRIMARY},
    "error": {"backgroundColor": "#fbebeb", "borderColor": CRITICAL, "textColor": TEXT_PRIMARY},
}

events = []
for _, i in rows.iterrows():
    title = f"{i['company']} · {i['kind'] or 'Interview'}"
    if i["sync_state"] == "pending":
        title += " (syncing)"
    elif i["sync_state"] == "cancel_requested":
        title += " (cancelling)"
    events.append(
        {
            "id": str(i["id"]),
            "title": title,
            "start": to_local(i["starts_at"]).isoformat(),
            "end": to_local(i["ends_at"]).isoformat(),
            **STATE_STYLE.get(i["sync_state"], STATE_STYLE["synced"]),
        }
    )

options = {
    "initialView": "dayGridMonth",
    "headerToolbar": {
        "left": "today prev,next",
        "center": "title",
        "right": "dayGridMonth,timeGridWeek,listMonth",
    },
    "timeZone": LOCAL_TZ_NAME,
    "slotMinTime": "07:00:00",
    "slotMaxTime": "20:00:00",
    "nowIndicator": True,
    "height": 680,
}
if is_phone():
    # The month grid is cramped on a phone; open on the list and keep the toolbar short.
    options.update(
        {
            "initialView": "listMonth",
            "headerToolbar": {"left": "prev,next", "center": "title", "right": "listMonth,dayGridMonth"},
            "height": "auto",
        }
    )
result = calendar(
    events=events,
    options=options,
    custom_css=".fc-event { cursor: pointer; } .fc-toolbar-title { font-size: 1.2rem; }",
    key="interview_calendar",
)

st.caption(
    "Dark blue: on Google Calendar. Light blue: saved here, added to Google Calendar on the next inbox run "
    "(up to 2 hours)."
)

clicked = (result or {}).get("eventClick", {}).get("event", {}).get("id")
if clicked:
    st.session_state["calendar_selected"] = int(clicked)

selected_id = st.session_state.get("calendar_selected")
if selected_id is not None and not rows.empty and selected_id in set(rows["id"].astype(int)):
    i = rows[rows["id"] == selected_id].iloc[0]
    with st.container(border=True):
        st.subheader(f"{i['company']}: {i['role_title']}")
        st.markdown(
            f"**{i['kind'] or 'Interview'}** · {fmt(i['starts_at'])} to {fmt(i['ends_at'], '%I:%M %p').lstrip('0')}"
        )
        if i["location"]:
            loc = i["location"]
            st.markdown(f"Where: [{loc}]({loc})" if str(loc).startswith("http") else f"Where: {loc}")
        if i["interviewers"]:
            st.markdown(f"With: {i['interviewers']}")
        if i["notes"]:
            st.markdown(i["notes"])
        state_text = {
            "synced": "On Google Calendar",
            "pending": "Waiting for the next inbox run to add it to Google Calendar",
            "cancel_requested": "Will be removed from Google Calendar on the next run",
            "error": "The agent couldn't sync this one. Edit and save it to retry",
        }.get(i["sync_state"], i["sync_state"])
        st.caption(state_text)

        b1, b2, _ = st.columns([1, 1, 4])
        if b1.button("Edit", icon=":material/edit:"):
            st.session_state["edit_interview"] = int(i["id"])
            st.switch_page("views/schedule.py")
        if i["sync_state"] != "cancel_requested" and b2.button("Cancel interview", icon=":material/event_busy:"):
            db.cancel_interview(int(i["id"]))
            st.session_state.pop("calendar_selected", None)
            st.toast("Interview cancelled.")
            st.rerun()
