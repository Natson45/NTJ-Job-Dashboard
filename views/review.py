"""Review: emails the agent wasn't sure about. Link them, fix the label, or dismiss."""

import pandas as pd
import streamlit as st

from jobdash import db
from jobdash.constants import EMAIL_LABEL_TEXT, EMAIL_LABELS
from jobdash.times import fmt
from jobdash.ui import app_options

st.title("Review")
st.caption("Emails the inbox agent couldn't match to an application, or wasn't confident about.")

emails = db.review_emails()
if emails.empty:
    st.success("Nothing to review.", icon=":material/check_circle:")
    st.stop()

options = app_options(db.applications())
ids = list(options.keys())

for _, e in emails.iterrows():
    mid = e["gmail_message_id"]
    with st.container(border=True):
        st.markdown(f"**{e['subject'] or '(no subject)'}**")
        conf = f" · agent confidence {e['confidence']:.0%}" if pd.notna(e["confidence"]) else ""
        st.caption(f"{fmt(e['received_at'])} · {e['sender'] or ''}{conf}")
        if e["summary"]:
            st.write(e["summary"])
        if e["gmail_url"]:
            st.link_button("Open in Gmail", e["gmail_url"], icon=":material/open_in_new:")

        with st.form(f"review_{mid}"):
            c1, c2 = st.columns([3, 2])
            current_app = int(e["application_id"]) if pd.notna(e["application_id"]) else None
            app_choice = c1.selectbox(
                "Application",
                ids,
                index=ids.index(current_app) if current_app in ids else None,
                format_func=lambda k: options[k],
                placeholder="Pick the application (leave empty if none)",
                key=f"app_{mid}",
            )
            label = c2.selectbox(
                "What is it?",
                EMAIL_LABELS,
                index=EMAIL_LABELS.index(e["label"]) if e["label"] in EMAIL_LABELS else 0,
                format_func=lambda k: EMAIL_LABEL_TEXT[k],
                key=f"label_{mid}",
            )
            apply_status = st.checkbox(
                "Also update the application's status to match (only if it moves forward)",
                value=True,
                key=f"apply_{mid}",
            )
            saved = st.form_submit_button("Save", type="primary")

        if saved:
            if label != "not_job" and app_choice is None:
                st.error("Pick an application, or set the type to “Not job-related”.")
            else:
                db.resolve_review(mid, app_choice if label != "not_job" else None, label, apply_status)
                st.toast("Saved.")
                st.rerun()
