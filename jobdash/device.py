"""Detect phones so pages can adjust their layout. Computers are never affected."""

import re

import streamlit as st

_PHONE = re.compile(r"iPhone|iPod|Android.*Mobile|Windows Phone|Mobile Safari", re.I)


def is_phone() -> bool:
    try:
        agent = st.context.headers.get("User-Agent", "") or ""
    except Exception:  # noqa: BLE001  (no request context, e.g. tests)
        return False
    return bool(_PHONE.search(agent)) and "iPad" not in agent
