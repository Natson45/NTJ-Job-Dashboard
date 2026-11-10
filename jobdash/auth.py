"""Google sign-in, using Streamlit's built-in st.login(), limited to ALLOWED_EMAILS.

* Google handles the password (and your 2-step verification, if it's on).
* Streamlit keeps you signed in with its own signed, httpOnly cookie (about 30 days),
  which JavaScript on the page can't read.
* Only addresses listed in ALLOWED_EMAILS (.env or Streamlit Secrets) get past the sign-in page.

Setup: .streamlit/secrets.toml holds the [auth] block (see README, "Sign-in").
"""

from __future__ import annotations

import os

import streamlit as st
from dotenv import load_dotenv


class AuthConfigError(RuntimeError):
    pass


def _normalize(email: str) -> str:
    """Gmail ignores dots and anything after '+', so compare addresses the same way."""
    email = email.strip().lower()
    local, _, domain = email.partition("@")
    if domain in ("gmail.com", "googlemail.com"):
        local = local.split("+", 1)[0].replace(".", "")
        domain = "gmail.com"
    return f"{local}@{domain}"


def _allowed() -> set[str]:
    load_dotenv(override=True)  # re-read .env so edits apply without a restart
    configured = os.environ.get("ALLOWED_EMAILS", "").strip()
    if not configured:
        try:
            configured = str(st.secrets.get("ALLOWED_EMAILS", "")).strip()
        except FileNotFoundError:
            configured = ""
    return {_normalize(e) for e in configured.split(",") if e.strip()}


def _auth_configured() -> bool:
    try:
        auth = st.secrets.get("auth", {})
    except Exception:  # noqa: BLE001  (no secrets.toml at all)
        return False
    needed = ("redirect_uri", "cookie_secret", "client_id", "client_secret", "server_metadata_url")
    return all(str(auth.get(k, "")).strip() and "PASTE" not in str(auth.get(k, "")) for k in needed)


def require_login() -> str:
    """Return the signed-in email, or show the sign-in page and stop."""
    allowed = _allowed()
    if not allowed:
        raise AuthConfigError(
            "ALLOWED_EMAILS is empty. Add your Google email to .env (local) or "
            "Streamlit Secrets at the top level (deployed app; see README, Sign-in)."
        )
    if not _auth_configured():
        raise AuthConfigError(
            "Google sign-in isn't set up yet: fill in client_id and client_secret in "
            ".streamlit/secrets.toml (see README, Sign-in)."
        )

    if not st.user.is_logged_in:
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            st.title("Job Dashboard")
            st.caption("Sign in with your Google account to continue.")
            st.button(
                "Sign in with Google",
                type="primary",
                icon=":material/login:",
                on_click=st.login,
                use_container_width=True,
            )
        st.stop()

    email = str(st.user.get("email") or "").lower()
    verified = st.user.get("email_verified", True)
    if _normalize(email) not in allowed or verified is False:
        _, mid, _ = st.columns([1, 2, 1])
        with mid:
            st.title("Job Dashboard")
            st.error(f"{email or 'This account'} doesn't have access to this dashboard.")
            st.button("Sign out", on_click=st.logout, use_container_width=True)
        st.stop()
    return email


def sign_out() -> None:
    st.logout()
