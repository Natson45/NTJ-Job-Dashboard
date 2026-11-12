"""Database access for the dashboard.

Connects to the Postgres database with DATABASE_URL (see .env.example).
All reads are cached for a short time; every write clears the cache.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator

import pandas as pd
import psycopg
import streamlit as st
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()

READ_TTL = 60  # seconds


class ConfigError(RuntimeError):
    pass


@st.cache_resource(show_spinner=False)
def _connect() -> psycopg.Connection:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise ConfigError(
            "DATABASE_URL is not set. Copy .env.example to .env and add your Postgres connection string."
        )
    # prepare_threshold=None keeps this working through Postgres connection poolers.
    return psycopg.connect(url, autocommit=True, row_factory=dict_row, prepare_threshold=None)


def conn() -> psycopg.Connection:
    c = _connect()
    if c.closed or c.broken:
        _connect.clear()
        c = _connect()
    return c


def rows(sql: str, params: tuple | dict | None = None) -> list[dict[str, Any]]:
    with conn().cursor() as cur:
        cur.execute(sql, params)
        return list(cur.fetchall()) if cur.description else []


def frame(sql: str, params: tuple | dict | None = None) -> pd.DataFrame:
    return pd.DataFrame(rows(sql, params))


@contextmanager
def tx(actor: str = "manual") -> Iterator[psycopg.Cursor]:
    """A transaction whose status changes are logged as made by `actor`."""
    c = conn()
    with c.transaction():
        with c.cursor() as cur:
            cur.execute("select set_config('jobs_nathan_dashboard.actor', %s, true)", (actor,))
            yield cur
    st.cache_data.clear()


# ---------------------------------------------------------------- reads


@st.cache_data(ttl=READ_TTL, show_spinner=False)
def companies() -> pd.DataFrame:
    return frame("select id, name from jobs_nathan_dashboard.companies order by lower(name)")


@st.cache_data(ttl=READ_TTL, show_spinner=False)
def applications() -> pd.DataFrame:
    return frame(
        """
        select a.id, c.name as company, a.role_title, a.status::text as status, a.track,
               a.location, a.applied_on, a.last_email_at, a.next_step, a.next_step_at,
               a.req_id, a.created_by, a.updated_at,
               (select count(*) from jobs_nathan_dashboard.emails e where e.application_id = a.id) as emails
        from jobs_nathan_dashboard.applications a
        join jobs_nathan_dashboard.companies c on c.id = a.company_id
        order by coalesce(a.last_email_at, a.created_at) desc
        """
    )


@st.cache_data(ttl=READ_TTL, show_spinner=False)
def application(app_id: int) -> dict[str, Any] | None:
    found = rows(
        """
        select a.*, a.status::text as status, c.name as company
        from jobs_nathan_dashboard.applications a join jobs_nathan_dashboard.companies c on c.id = a.company_id
        where a.id = %s
        """,
        (app_id,),
    )
    return found[0] if found else None


@st.cache_data(ttl=READ_TTL, show_spinner=False)
def status_history(app_id: int) -> pd.DataFrame:
    return frame(
        """
        select from_status::text as from_status, to_status::text as to_status,
               changed_at, changed_by, email_id
        from jobs_nathan_dashboard.status_history where application_id = %s
        order by changed_at
        """,
        (app_id,),
    )


@st.cache_data(ttl=READ_TTL, show_spinner=False)
def emails_for(app_id: int) -> pd.DataFrame:
    return frame(
        """
        select gmail_message_id, received_at, sender, subject, summary, label,
               confidence, needs_review, gmail_url
        from jobs_nathan_dashboard.emails where application_id = %s
        order by received_at desc
        """,
        (app_id,),
    )


@st.cache_data(ttl=READ_TTL, show_spinner=False)
def interviews(start: datetime | None = None, end: datetime | None = None) -> pd.DataFrame:
    return frame(
        """
        select i.id, i.application_id, c.name as company, a.role_title, i.kind,
               i.starts_at, i.ends_at, i.location, i.interviewers, i.notes, i.source,
               i.gcal_event_id, i.sync_state
        from jobs_nathan_dashboard.interviews i
        join jobs_nathan_dashboard.applications a on a.id = i.application_id
        join jobs_nathan_dashboard.companies c on c.id = a.company_id
        where (%(start)s::timestamptz is null or i.ends_at >= %(start)s)
          and (%(end)s::timestamptz is null or i.starts_at < %(end)s)
        order by i.starts_at
        """,
        {"start": start, "end": end},
    )


@st.cache_data(ttl=READ_TTL, show_spinner=False)
def review_emails() -> pd.DataFrame:
    return frame(
        """
        select e.gmail_message_id, e.received_at, e.sender, e.subject, e.summary,
               e.label, e.confidence, e.gmail_url, e.application_id
        from jobs_nathan_dashboard.emails e
        where e.needs_review
        order by e.received_at desc
        """
    )


@st.cache_data(ttl=READ_TTL, show_spinner=False)
def funnel_counts() -> pd.DataFrame:
    """How many applications ever reached each stage (from status history)."""
    return frame(
        """
        with reached as (
          select a.id,
                 max(case h.to_status
                       when 'applied' then 1 when 'screen' then 2 when 'assessment' then 3
                       when 'interview' then 4 when 'offer' then 5 else 0 end) as stage
          from jobs_nathan_dashboard.applications a
          left join jobs_nathan_dashboard.status_history h on h.application_id = a.id
          group by a.id
        )
        select s.stage_name as stage, count(r.id) as applications
        from (values (1,'applied'),(2,'screen'),(3,'assessment'),(4,'interview'),(5,'offer'))
             as s(stage_no, stage_name)
        left join reached r on r.stage >= s.stage_no
        group by s.stage_no, s.stage_name
        order by s.stage_no
        """
    )


@st.cache_data(ttl=READ_TTL, show_spinner=False)
def application_paths() -> pd.DataFrame:
    """Each application's current status and the statuses it moved through, in order."""
    return frame(
        """
        select a.id, a.status::text as status,
               coalesce(array_agg(h.to_status::text order by h.changed_at, h.id)
                        filter (where h.id is not null), '{}') as path
        from jobs_nathan_dashboard.applications a
        left join jobs_nathan_dashboard.status_history h on h.application_id = a.id
        group by a.id, a.status
        """
    )


@st.cache_data(ttl=READ_TTL, show_spinner=False)
def last_run() -> dict[str, Any] | None:
    found = rows(
        "select * from jobs_nathan_dashboard.agent_runs where finished_at is not null order by finished_at desc limit 1"
    )
    return found[0] if found else None


# ---------------------------------------------------------------- writes


def company_id_for(cur: psycopg.Cursor, name: str) -> int:
    cur.execute(
        """
        insert into jobs_nathan_dashboard.companies (name) values (%s)
        on conflict (name) do update set name = excluded.name
        returning id
        """,
        (name.strip(),),
    )
    return cur.fetchone()["id"]


def create_application(values: dict[str, Any]) -> int:
    with tx("manual") as cur:
        company_id = company_id_for(cur, values.pop("company"))
        cur.execute(
            """
            insert into jobs_nathan_dashboard.applications
              (company_id, role_title, req_id, location, track, status, applied_on,
               next_step, next_step_at, notes, created_by)
            values (%(company_id)s, %(role_title)s, %(req_id)s, %(location)s, %(track)s,
                    %(status)s, %(applied_on)s, %(next_step)s, %(next_step_at)s, %(notes)s, 'manual')
            returning id
            """,
            {"company_id": company_id, **values},
        )
        return cur.fetchone()["id"]


def update_application(app_id: int, values: dict[str, Any]) -> None:
    with tx("manual") as cur:
        cur.execute(
            """
            update jobs_nathan_dashboard.applications set
              role_title = %(role_title)s, req_id = %(req_id)s, location = %(location)s,
              track = %(track)s, status = %(status)s, applied_on = %(applied_on)s,
              next_step = %(next_step)s, next_step_at = %(next_step_at)s, notes = %(notes)s
            where id = %(id)s
            """,
            {"id": app_id, **values},
        )


def save_interview(values: dict[str, Any], interview_id: int | None = None) -> int:
    """Create or edit an interview. Either way it goes back to 'pending' so the agent syncs it."""
    with tx("manual") as cur:
        if interview_id is None:
            cur.execute(
                """
                insert into jobs_nathan_dashboard.interviews
                  (application_id, kind, starts_at, ends_at, location, interviewers, notes, source, sync_state)
                values (%(application_id)s, %(kind)s, %(starts_at)s, %(ends_at)s, %(location)s,
                        %(interviewers)s, %(notes)s, 'manual', 'pending')
                returning id
                """,
                values,
            )
            new_id = cur.fetchone()["id"]
        else:
            cur.execute(
                """
                update jobs_nathan_dashboard.interviews set
                  application_id = %(application_id)s, kind = %(kind)s, starts_at = %(starts_at)s,
                  ends_at = %(ends_at)s, location = %(location)s, interviewers = %(interviewers)s,
                  notes = %(notes)s, sync_state = 'pending'
                where id = %(id)s
                """,
                {"id": interview_id, **values},
            )
            new_id = interview_id
        # Scheduling an interview moves an earlier-stage application to 'interview'.
        cur.execute(
            """
            update jobs_nathan_dashboard.applications set status = 'interview'
            where id = %s and status in ('applied','screen','assessment')
            """,
            (values["application_id"],),
        )
        return new_id


def cancel_interview(interview_id: int) -> None:
    with tx("manual") as cur:
        cur.execute(
            """
            update jobs_nathan_dashboard.interviews set
              sync_state = case when gcal_event_id is null then 'cancelled' else 'cancel_requested' end
            where id = %s
            """,
            (interview_id,),
        )


def resolve_review(message_id: str, application_id: int | None, label: str, apply_status: bool) -> None:
    from .constants import LABEL_TO_STATUS, OPEN_STATUSES

    with tx("manual") as cur:
        cur.execute("select set_config('jobs_nathan_dashboard.email_id', %s, true)", (message_id,))
        cur.execute(
            """
            update jobs_nathan_dashboard.emails set application_id = %s, label = %s, needs_review = false
            where gmail_message_id = %s
            """,
            (application_id, label, message_id),
        )
        new_status = LABEL_TO_STATUS.get(label)
        if apply_status and application_id and new_status:
            cur.execute(
                "select status::text as status from jobs_nathan_dashboard.applications where id = %s", (application_id,)
            )
            current = cur.fetchone()["status"]
            moves_forward = (
                current in OPEN_STATUSES
                and (new_status == "rejected" or OPEN_STATUSES.index(new_status) > OPEN_STATUSES.index(current))
            )
            if moves_forward:
                cur.execute(
                    "update jobs_nathan_dashboard.applications set status = %s where id = %s", (new_status, application_id)
                )
