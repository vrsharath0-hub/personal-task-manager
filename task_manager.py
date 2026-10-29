"""SQLite persistence and validation for the local task manager."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB_PATH = Path(__file__).with_name("tasks.db")
CATEGORIES = ("Assignment", "Exam", "Project", "Personal")
PRIORITIES = ("High", "Medium", "Low")
STATUSES = ("Pending", "In Progress", "Completed")
_HASH_ROUNDS = 310_000


def _connect(db_path: str | Path = DEFAULT_DB_PATH) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _password_digest(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _HASH_ROUNDS)


def init_db(db_path: str | Path = DEFAULT_DB_PATH) -> None:
    """Create the schema and ensure the documented local test account exists."""
    with _connect(db_path) as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL CHECK(length(title) BETWEEN 1 AND 160),
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                due_date TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_tasks_user_due
                ON tasks(user_id, due_date);
            """
        )
        existing = connection.execute(
            "SELECT id FROM users WHERE username = ?", ("admin",)
        ).fetchone()
        if existing is None:
            create_user("admin", "admin123", db_path)


def create_user(
    username: str, password: str, db_path: str | Path = DEFAULT_DB_PATH
) -> int:
    username = username.strip()
    if not username or len(username) > 80:
        raise ValueError("Username must be between 1 and 80 characters.")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters.")
    salt = secrets.token_bytes(16)
    with _connect(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO users (username, password_salt, password_hash, created_at) "
            "VALUES (?, ?, ?, ?)",
            (username, salt, _password_digest(password, salt), _now()),
        )
        return int(cursor.lastrowid)


def authenticate(
    username: str, password: str, db_path: str | Path = DEFAULT_DB_PATH
) -> dict[str, Any] | None:
    with _connect(db_path) as connection:
        user = connection.execute(
            "SELECT id, username, password_salt, password_hash "
            "FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if user is None:
        return None
    candidate = _password_digest(password, user["password_salt"])
    if not hmac.compare_digest(candidate, user["password_hash"]):
        return None
    return {"id": user["id"], "username": user["username"]}


def _validate_task(
    title: str,
    category: str,
    priority: str,
    due_date: str,
    status: str,
) -> tuple[str, str, str, str, str]:
    title = title.strip()
    if not title or len(title) > 160:
        raise ValueError("Task name must be between 1 and 160 characters.")
    if category not in CATEGORIES:
        raise ValueError("Choose a valid task category.")
    if priority not in PRIORITIES:
        raise ValueError("Choose High, Medium, or Low priority.")
    if status not in STATUSES:
        raise ValueError("Choose a valid task status.")
    try:
        normalized_due_date = date.fromisoformat(str(due_date)).isoformat()
    except ValueError as error:
        raise ValueError("Enter a valid due date.") from error
    return title, category, priority, normalized_due_date, status


def add_task(
    user_id: int,
    title: str,
    category: str,
    priority: str,
    due_date: str,
    status: str = "Pending",
    description: str = "",
    db_path: str | Path = DEFAULT_DB_PATH,
) -> int:
    title, category, priority, due_date, status = _validate_task(
        title, category, priority, due_date, status
    )
    now = _now()
    with _connect(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO tasks "
            "(user_id, title, description, category, priority, due_date, status, "
            "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (user_id, title, description.strip(), category, priority, due_date, status, now, now),
        )
        return int(cursor.lastrowid)


def list_tasks(
    user_id: int, db_path: str | Path = DEFAULT_DB_PATH
) -> list[dict[str, Any]]:
    with _connect(db_path) as connection:
        rows = connection.execute(
            "SELECT id, title, description, category, priority, due_date, status, "
            "created_at, updated_at FROM tasks WHERE user_id = ? ORDER BY due_date, id",
            (user_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def update_task(
    user_id: int,
    task_id: int,
    title: str,
    category: str,
    priority: str,
    due_date: str,
    status: str,
    description: str = "",
    db_path: str | Path = DEFAULT_DB_PATH,
) -> bool:
    title, category, priority, due_date, status = _validate_task(
        title, category, priority, due_date, status
    )
    with _connect(db_path) as connection:
        cursor = connection.execute(
            "UPDATE tasks SET title = ?, description = ?, category = ?, priority = ?, "
            "due_date = ?, status = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (
                title,
                description.strip(),
                category,
                priority,
                due_date,
                status,
                _now(),
                task_id,
                user_id,
            ),
        )
        return cursor.rowcount == 1


def delete_task(
    user_id: int, task_id: int, db_path: str | Path = DEFAULT_DB_PATH
) -> bool:
    with _connect(db_path) as connection:
        cursor = connection.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)
        )
        return cursor.rowcount == 1