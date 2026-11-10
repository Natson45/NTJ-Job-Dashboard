"""Applications: filterable list, detail view with history and emails, add/edit."""

from datetime import date, time, timedelta

import pandas as pd
import streamlit as st

from jobdash import db
from jobdash.constants import EMAIL_LABEL_TEXT, STATUSES, TRACKS
from jobdash.device import is_phone
from jobdash.times import fmt, fmt_date, local_to_utc, to_local
from jobdash.ui import none_if_blank, status_text

st.title("Applications")

apps = db.applications()


# ---------------------------------------------------------------- add form
def application_form(key: str, current: dict | None = None) -> dict | None:
    """Shared add/edit form. Returns the values when submitted, else None."""
    current = current or {}
    with st.form(key, clear_on_submit=current == {}):
        c1, c2 = st.columns(2)
        if not current:
            names = db.companies()["name"].tolist() if not db.companies().empty else []
            company_choice = c1.selectbox("Company", ["➕ New company…"] + names, index=None, placeholder="Pick or add")
            new_company = c1.text_input("New company name", placeholder="Only if it's not in the list")
        role = c2.text_input("Role title", value=current.get("role_title") or "")
        c3, c4, c5 = st.columns(3)
        status = c3.selectbox(
            "Status", STATUSES, index=STATUSES.index(current.get("status", "applied")), format_func=status_text
        )
        track_options = [""] + TRACKS
        track = c4.selectbox(
            "Track",
            track_options,
            index=track_options.index(current["track"]) if current.get("track") in track_options else 0,
        )
        applied_on = c5.date_input("Applied on", value=current.get("applied_on") or date.today())
        c6, c7 = st.columns(2)
        location = c6.text_input("Location", value=current.get("location") or "")
        req_id = c7.text_input("Requisition ID", value=current.get("req_id") or "")
        c8, c9, c10 = st.columns([2, 1, 1])
        next_step = c8.text_input("Next step", value=current.get("next_step") or "")
        existing_due = to_local(current.get("next_step_at"))
        has_due = c9.checkbox("Has a due date", value=existing_due is not None)
        due_date = c10.date_input("Due", value=existing_due.date() if existing_due else date.today() + timedelta(days=3))
        notes = st.text_area("Notes", value=current.get("notes") or "", height=100)
        submitted = st.form_submit_button("Save", type="primary")

    if not submitted:
        return None
    values = {
        "role_title": role.strip(),
        "req_id": none_if_blank(req_id),
        "location": none_if_blank(location),
        "track": none_if_blank(track),
        "status": status,
        "applied_on": applied_on,
        "next_step": none_if_blank(next_step),
        "next_step_at": local_to_utc(due_date, time(17, 0)) if has_due else None,
        "notes": none_if_blank(notes),
    }
    if not current:
        company = new_company.strip() if company_choice in (None, "➕ New company…") else company_choice
        if not company:
            st.error("Pick a company or type a new one.")
            return None
        values["company"] = company
    if not values["role_title"]:
        st.error("Role title is required.")
        return None
    return values


with st.expander("Add an application by hand", icon=":material/add:"):
    st.caption("For jobs where no acknowledgment email came in. The agent will still link later emails to it.")
    new_values = application_form("add_app")
    if new_values:
        new_id = None
        try:
            new_id = db.create_application(new_values)
        except Exception as err:  # noqa: BLE001
            if "applications_dedup" in str(err):
                st.error("That company + role (+ requisition ID) is already tracked.")
            else:
                st.error(f"Could not save: {err}")
        if new_id is not None:
            st.session_state["selected_app"] = new_id
            st.toast("Application added.")
            st.rerun()

if apps.empty:
    st.info("No applications yet.")
    st.stop()

# ---------------------------------------------------------------- filters + table
f1, f2, f3, f4 = st.columns([2, 2, 2, 3])
status_filter = f1.multiselect("Status", STATUSES, format_func=status_text, placeholder="All")
track_filter = f2.multiselect("Track", sorted(apps["track"].dropna().unique()), placeholder="All")
company_filter = f3.multiselect("Company", sorted(apps["company"].unique()), placeholder="All")
search = f4.text_input("Search role", placeholder="e.g. machine learning")

view = apps.copy()
if status_filter:
    view = view[view["status"].isin(status_filter)]
if track_filter:
    view = view[view["track"].isin(track_filter)]
if company_filter:
    view = view[view["company"].isin(company_filter)]
if search:
    view = view[view["role_title"].str.contains(search, case=False, na=False)]

table = view[["id", "company", "role_title", "status", "track", "location", "applied_on", "last_email_at", "emails"]].copy()
table["status"] = table["status"].map(status_text)
table["applied_on"] = table["applied_on"].map(fmt_date)
table["last_email_at"] = table["last_email_at"].map(lambda d: fmt(d) if pd.notna(d) else "—")

st.caption(f"{len(view)} of {len(apps)} applications · click any cell to open that application")
# Work out which row is selected before drawing, so it can be shaded.
grid_cells = ((st.session_state.get("apps_grid") or {}).get("selection") or {}).get("cells") or []
if grid_cells and grid_cells[0][0] < len(table):
    st.session_state["selected_app"] = int(table.iloc[grid_cells[0][0]]["id"])
selected_id = st.session_state.get("selected_app")

SELECTED_ROW = "background-color: #cde2fb; font-weight: 600"
styled = table.style.apply(
    lambda row: [SELECTED_ROW if int(row["id"]) == selected_id else "" for _ in row], axis=1
)

st.dataframe(
    styled,
    key="apps_grid",
    hide_index=True,
    use_container_width=True,
    on_select="rerun",
    selection_mode="single-cell",  # clicking any cell opens that row
    column_config={
        "id": None,
        "company": "Company",
        "role_title": "Role",
        "status": "Status",
        "track": "Track",
        "location": "Location",
        "applied_on": "Applied",
        "last_email_at": "Last email",
        "emails": st.column_config.NumberColumn("Emails", width="small"),
        # On a phone, drop the least useful columns so less sideways swiping is needed.
        **({"track": None, "location": None, "emails": None} if is_phone() else {}),
    },
)

app_id = st.session_state.get("selected_app")
if app_id is None or app_id not in set(apps["id"].astype(int)):
    st.stop()

# ---------------------------------------------------------------- detail
app = db.application(app_id)
if app is None:
    st.stop()

st.divider()
st.header(f"{app['company']}: {app['role_title']}")
st.caption(
    f"Status: **{status_text(app['status'])}** · Applied {fmt_date(app['applied_on'])}"
    + (f" · Req {app['req_id']}" if app.get("req_id") else "")
    + (f" · {app['location']}" if app.get("location") else "")
)
if app.get("next_step"):
    due = f" (due {fmt(app['next_step_at'])})" if app.get("next_step_at") else ""
    st.info(f"Next step: {app['next_step']}{due}", icon=":material/flag:")

tab_emails, tab_history, tab_edit = st.tabs(["Emails", "Status history", "Edit"])

with tab_emails:
    emails = db.emails_for(app_id)
    if emails.empty:
        st.caption("No emails linked yet.")
    for _, e in emails.iterrows():
        with st.container(border=True):
            top = st.columns([3, 1])
            top[0].markdown(f"**{e['subject'] or '(no subject)'}**")
            top[1].markdown(f":blue-badge[{EMAIL_LABEL_TEXT.get(e['label'], e['label'])}]")
            st.caption(f"{fmt(e['received_at'])} · {e['sender'] or ''}")
            if e["summary"]:
                st.write(e["summary"])
            if e["gmail_url"]:
                st.link_button("Open in Gmail", e["gmail_url"], icon=":material/open_in_new:")

with tab_history:
    hist = db.status_history(app_id)
    if hist.empty:
        st.caption("No status changes recorded.")
    for _, h in hist.iterrows():
        move = (
            f"{status_text(h['from_status'])} → **{status_text(h['to_status'])}**"
            if h["from_status"]
            else f"Created as **{status_text(h['to_status'])}**"
        )
        who = "by you" if h["changed_by"] == "manual" else "from an email" if h["email_id"] else "by the agent"
        st.markdown(f"- {fmt(h['changed_at'])}: {move} ({who})")

with tab_edit:
    edited = application_form(f"edit_{app_id}", current=app)
    if edited:
        saved = False
        try:
            db.update_application(app_id, edited)
            saved = True
        except Exception as err:  # noqa: BLE001
            st.error(f"Could not save: {err}")
        if saved:
            st.toast("Saved.")
            st.rerun()
