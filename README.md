# Studylist

A local task manager for keeping student work organized. Studylist uses Streamlit for the interface and SQLite for persistent storage. It runs on your computer and does not require an account with an online service or an internet connection after setup.

## Features

- Add, edit, complete, reopen, and delete tasks
- Track category, priority, due date, notes, and status
- Filter by status, priority, and category; sort by due date, priority, or creation time
- Dashboard with total, pending, in-progress, completed, and overdue counts
- Overdue and upcoming deadlines highlighted in the task list
- Local SQLite storage with per-user task isolation and hashed passwords

## Run locally

Python 3.10 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

On macOS or Linux, activate with `source .venv/bin/activate` instead. After dependencies are installed, the app itself works offline.

Sign in with the database-backed starter account `admin` / `admin123`, or create a separate local account from the sign-in screen. Each account sees only its own tasks, and passwords are stored as salted hashes. The SQLite database is created as `tasks.db` beside the application on first run. Keep that file private; it contains the local account and task data. The starter account is intended for local testing, not public deployment.

## Tests

```powershell
python -m pytest
```

Tests use temporary databases and do not modify the application's `tasks.db`.