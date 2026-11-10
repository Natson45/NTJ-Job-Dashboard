"""Pipeline: KPIs, funnel, what needs attention, upcoming interviews."""

from datetime import timedelta

import pandas as pd
import streamlit as st

from jobdash import db
from jobdash.constants import OPEN_STATUSES
from jobdash.device import is_phone
from jobdash.flow import sankey_figure
from jobdash.times import fmt, fmt_date, now_local

st.title("Pipeline")

apps = db.applications()
now = now_local()
week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
upcoming = db.interviews(start=now, end=now + timedelta(days=14))
reviews = db.review_emails()

if apps.empty:
    st.info(
        "No applications yet. The inbox agent creates them from acknowledgment emails, "
        "or you can add one on the Applications page."
    )

# ---------------------------------------------------------------- KPI row
active = apps[apps["status"].isin(OPEN_STATUSES)] if not apps.empty else apps
applied_this_week = 0
if not apps.empty:
    applied_on = pd.to_datetime(apps["applied_on"])
    applied_this_week = int((applied_on >= week_start.replace(tzinfo=None)).sum())
interviews_this_week = 0
if not upcoming.empty:
    starts = pd.to_datetime(upcoming["starts_at"], utc=True)
    end_of_week = week_start + timedelta(days=7)
    interviews_this_week = int(((starts >= now) & (starts < end_of_week)).sum())

k1, k2, k3, k4 = st.columns(4)
k1.metric("Active applications", len(active))
k2.metric("Applied this week", applied_this_week)
k3.metric("Interviews this week", interviews_this_week)
k4.metric("Offers", int((apps["status"] == "offer").sum()) if not apps.empty else 0)

st.divider()

# ---------------------------------------------------------------- flow
st.subheader("Where your applications went")
flow = sankey_figure(db.application_paths())
if flow is None:
    st.caption("The diagram appears once there are applications.")
else:
    if is_phone():
        flow.update_layout(height=520, font=dict(size=11))  # taller so the bands stay readable
    st.plotly_chart(flow, use_container_width=True, config={"displayModeBar": False})
    st.caption("Each band is a group of applications moving between stages. Hover a band or a stage for its count.")

st.divider()
left, right = st.columns([3, 2], gap="large")

# ---------------------------------------------------------------- needs attention
with left:
    st.subheader("Needs attention")
    items: list[str] = []

    if not reviews.empty:
        items.append(f"**{len(reviews)} email(s) to review**: open the Review page")

    if not apps.empty:
        due = apps[apps["next_step_at"].notna() & apps["status"].isin(OPEN_STATUSES)].copy()
        if not due.empty:
            due["next_step_at"] = pd.to_datetime(due["next_step_at"], utc=True)
            due = due[due["next_step_at"] <= now + timedelta(days=3)]
            for _, r in due.sort_values("next_step_at").iterrows():
                items.append(
                    f"**{r['company']}**, {r['role_title']}: {r['next_step'] or 'next step'} "
                    f"by {fmt(r['next_step_at'])}"
                )

        quiet = apps[(apps["status"] == "applied") & apps["applied_on"].notna()].copy()
        if not quiet.empty:
            quiet["applied_on"] = pd.to_datetime(quiet["applied_on"])
            cutoff = (now - timedelta(days=14)).replace(tzinfo=None)
            quiet = quiet[quiet["applied_on"] <= cutoff]
            if len(quiet):
                items.append(f"**{len(quiet)} application(s)** with no reply in 14+ days: consider following up")

    if items:
        for item in items:
            st.markdown(f"- {item}")
    else:
        st.caption("Nothing due right now.")

with right:
    st.subheader("Next 14 days")
    if upcoming.empty:
        st.caption("No interviews scheduled.")
    else:
        for _, i in upcoming.iterrows():
            pending = "" if i["sync_state"] == "synced" else "  ·  :orange[not yet on Google Calendar]"
            st.markdown(
                f"**{fmt(i['starts_at'])}**  \n"
                f"{i['company']}, {i['role_title']} ({i['kind'] or 'interview'}){pending}"
            )

# ---------------------------------------------------------------- recent activity
st.divider()
st.subheader("Recently updated")
if apps.empty:
    st.caption("Nothing yet.")
else:
    recent = apps.head(10)[["company", "role_title", "status", "applied_on", "last_email_at"]].copy()
    recent["status"] = recent["status"].str.capitalize()
    recent["applied_on"] = recent["applied_on"].map(fmt_date)
    recent["last_email_at"] = recent["last_email_at"].map(lambda d: fmt(d) if pd.notna(d) else "—")
    st.dataframe(
        recent,
        hide_index=True,
        use_container_width=True,
        column_config={
            "company": "Company",
            "role_title": "Role",
            "status": "Status",
            "applied_on": "Applied",
            "last_email_at": "Last email",
        },
    )
