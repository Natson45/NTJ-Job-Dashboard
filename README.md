# Job Dashboard

A Streamlit dashboard for tracking job applications from first acknowledgment through screens, interviews, offers, rejections and ghosting.

- **Data:** Supabase Postgres, `jobs` schema (companies, applications, emails, status history, interviews, agent runs).
- **Inbox agent (separate from this repo):** a scheduled Claude task reads a dedicated job inbox, creates and updates applications, and books interviews in Google Calendar. This app reads and edits the same tables.
- **Sign-in:** Google, restricted to the emails in `ALLOWED_EMAILS`.

No secrets live in this repo. Locally they are in `.env` and `.streamlit/secrets.toml` (both gitignored); on Streamlit Community Cloud they go in the app's **Secrets**.

## Pages

| Page | What it does |
| --- | --- |
| Pipeline | KPIs, a flow chart of where applications went, what needs attention, interviews in the next 14 days |
| Applications | Filter the list; click any cell to open an application: its emails, status history and an edit form. Add one by hand |
| Calendar | Month / week / list view of interviews. Click one for details, edit or cancel |
| Schedule interview | Add or edit an interview (Central time) |
| Review | Emails the agent wasn't sure about: link them, fix the type, update the status |

On phones the layout adjusts (list-view calendar, fewer table columns, taller flow chart). Computers are unaffected.

## Configuration

| Setting | Where (local) | Where (Community Cloud) | Used by |
| --- | --- | --- | --- |
| `DATABASE_URL` | `.env` | Secrets, top level | `jobdash/db.py` |
| `ALLOWED_EMAILS` | `.env` | Secrets, top level | `jobdash/auth.py` |
| `[auth]` block | `.streamlit/secrets.toml` | Secrets, `[auth]` table | Streamlit's `st.login()` |

`[auth]` block (same shape in both places):

```toml
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"   # or https://<your-app>.streamlit.app/oauth2callback
cookie_secret = "<long random string>"
client_id = "<from Google Cloud>.apps.googleusercontent.com"
client_secret = "<from Google Cloud>"
server_metadata_url = "https://accounts.google.com/.well-known/openid-configuration"
```

Generate a cookie secret with `python -c "import secrets; print(secrets.token_urlsafe(48))"`. Use a different one locally and in the cloud.

## Database access

The app connects as a limited Postgres role, `jobs_dashboard`, never the main `postgres` user. The role can read and write the `jobs` tables only (no deletes, no other schemas). Row Level Security is on for every table, with policies only for this role.

Set or rotate its password in the Supabase SQL Editor:

```sql
alter role jobs_dashboard with password '<letters-and-numbers-only>';
```

Then update `DATABASE_URL` locally and in the cloud Secrets.

## Google sign-in setup (one time)

1. In Google Cloud Console, create a project.
2. **Google Auth Platform → Branding:** app name and support email. **Audience:** External, publishing status Testing. Under **Test users**, add the account you will sign in with, using its exact address (Gmail dots matter on that screen).
3. **Clients → Create client → Web application.** Authorized redirect URIs:
   - `http://localhost:8501/oauth2callback` (local)
   - `https://<your-app>.streamlit.app/oauth2callback` (Community Cloud)
4. Put the client ID and secret in the `[auth]` block (locally and/or in cloud Secrets).
5. Set `ALLOWED_EMAILS`. Gmail addresses are compared ignoring dots and `+tags`.

While the Google app is in Testing, only listed test users can sign in at all; the app's own `ALLOWED_EMAILS` check is a second lock.

## Run locally (Windows)

1. Install Python 3.11+.
2. Double-click `start.bat`. The first run creates `.venv`, installs `requirements.txt`, creates `.env` from `.env.example` and opens it.
3. Fill in `.env` and `.streamlit/secrets.toml`, then run `start.bat` again. The dashboard opens at http://localhost:8501.

Keep the console window open while you use it; closing it stops the dashboard. Changes to `views/*.py` show on refresh; changes to `jobdash/*.py` need a restart.

## Deploy to Streamlit Community Cloud

1. Push this repo to GitHub (private is fine). Check that `.env` and `.streamlit/secrets.toml` are not committed.
2. share.streamlit.io → **Create app** → this repo, main file `app.py`, Python 3.12.
3. Paste `DATABASE_URL`, `ALLOWED_EMAILS` and the `[auth]` block (cloud `redirect_uri`) into **Secrets**.
4. Add the cloud redirect URI in Google Cloud, then reboot the app and sign in.

Free apps sleep after about 12 hours without visits; the next visit wakes them in under a minute.

## How interviews reach Google Calendar

Interviews saved here are stored as `pending` (light blue on the calendar). The inbox agent creates the Google Calendar event on its next run and marks it `synced` (dark blue). Cancelling works the same way. Interviews the agent finds in email go straight onto the calendar.

## Statuses

`applied → screen → assessment → interview → offer`, plus `rejected`, `withdrawn` and `ghosted` (no email for 45 days while still at `applied`; set by the agent). Every change is logged in `status_history` as `manual` (this app) or `agent`.

## Files

```
app.py                entry point: database check, sign-in, navigation, sidebar
views/                the five pages
jobdash/db.py         all SQL (reads cached 60 s; writes clear the cache)
jobdash/auth.py       Google sign-in + ALLOWED_EMAILS check
jobdash/flow.py       flow (Sankey) chart from status history
jobdash/device.py     phone detection for layout tweaks
jobdash/times.py      UTC in the database, Central on screen
jobdash/constants.py  statuses, email labels, colors
jobdash/ui.py         small shared helpers
start.bat             local launcher (Windows)
```
