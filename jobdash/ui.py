"""Small UI helpers shared by pages."""

from __future__ import annotations

import pandas as pd

from .constants import STATUS_LABEL


def app_label(row) -> str:
    return f"{row['company']} — {row['role_title']} (#{row['id']})"


def app_options(apps: pd.DataFrame, open_only: bool = False) -> dict[int, str]:
    if apps.empty:
        return {}
    if open_only:
        apps = apps[apps["status"].isin(["applied", "screen", "assessment", "interview", "offer"])]
    return {int(r["id"]): app_label(r) for _, r in apps.iterrows()}


def status_text(status: str | None) -> str:
    return STATUS_LABEL.get(status or "", status or "—")


def none_if_blank(value):
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value
