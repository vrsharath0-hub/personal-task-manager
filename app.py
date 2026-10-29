from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from typing import Any

import pandas as pd
import streamlit as st

from task_manager import (
    CATEGORIES,
    DEFAULT_DB_PATH,
    PRIORITIES,
    STATUSES,
    add_task,
    authenticate,
    create_user,
    delete_task,
    init_db,
    list_tasks,
    update_task,
)

st.set_page_config(
    page_title="Studylist | Task manager",
    page_icon="S",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root {
      --ink: #17231f; --paper: #f5f6f1; --green: #245c48; --lime: #d3ef77;
      --coral: #e46b58; --muted: #68756d; --line: #dce2d9;
    }
    .stApp { background: var(--paper); color: var(--ink); }
    [data-testid="stSidebar"] { background: #e8eee6; border-right: 1px solid var(--line); }
    [data-testid="stSidebar"] * { color: var(--ink); }
    h1, h2, h3 { font-family: 'Palatino Linotype', Georgia, serif !important; color: var(--ink); }
    h1 { font-size: 2.45rem !important; letter-spacing: 0 !important; }
    p, label, input, button, textarea, [data-testid="stMetricValue"] {
    font-family: 'Segoe UI', 'Trebuchet MS', sans-serif;
    }
    [data-testid="stMetric"] { background: white; border: 1px solid var(--line); border-radius: 6px; padding: 18px 20px; }
    [data-testid="stMetricLabel"] { color: var(--muted); font-size: .82rem; }
    [data-testid="stMetricValue"] { color: var(--green); font-size: 2rem; font-weight: 700; }
    div[data-testid="stForm"] { background: white; border: 1px solid var(--line); border-radius: 6px; padding: 20px; }
    div.stButton > button[kind="primary"], div[data-testid="stFormSubmitButton"] button {
      background: var(--green); border: 1px solid var(--green); color: white; border-radius: 5px;
      font-weight: 600; min-height: 2.65rem;
    }
    div.stButton > button[kind="primary"]:hover, div[data-testid="stFormSubmitButton"] button:hover {
      background: #174b38; border-color: #174b38; color: white;
    }
    div.stButton > button { border-radius: 5px; }
    [data-testid="stDataFrame"] { border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }
    .eyebrow { color: var(--green); font-family: Consolas, monospace; font-size: .72rem;
      letter-spacing: 0; text-transform: uppercase; margin-bottom: .35rem; }
    .page-subtitle { color: var(--muted); margin-top: -.6rem; margin-bottom: 1.5rem; }
    .login-mark { display: inline-flex; align-items: center; justify-content: center; width: 42px;
      height: 42px; background: var(--lime); color: var(--ink); border-radius: 50%;
    font-family: Consolas, monospace; font-weight: 500; margin-bottom: 18px; }
    .section-rule { border-top: 1px solid var(--line); margin: 1.25rem 0; }
    @media (max-width: 700px) { h1 { font-size: 2rem !important; } }
    </style>
    """,
    unsafe_allow_html=True,
)


def _due_label(task: dict[str, Any], today: date) -> str:
    due = date.fromisoformat(task["due_date"])
    if task["status"] == "Completed":
        return "Done"
    if due < today:
        return "Overdue"
    if due == today:
        return "Due today"
    if due <= today + timedelta(days=7):
        return "Coming up"
    return "Scheduled"


def _task_frame(tasks: list[dict[str, Any]]) -> pd.DataFrame:
    today = date.today()
    rows = [
        {
            "Task": task["title"],
            "Category": task["category"],
            "Priority": task["priority"],
            "Due date": task["due_date"],
            "Status": task["status"],
            "Deadline": _due_label(task, today),
        }
        for task in tasks
    ]
    return pd.DataFrame(rows, columns=["Task", "Category", "Priority", "Due date", "Status", "Deadline"])


def _show_login() -> None:
    _, center, _ = st.columns([1, 1.15, 1])
    with center:
        st.markdown('<div class="login-mark">S.</div>', unsafe_allow_html=True)
        st.markdown('<p class="eyebrow">A quieter way to keep up</p>', unsafe_allow_html=True)
        st.title("Studylist")
        st.markdown('<p class="page-subtitle">Your semester, in one place.</p>', unsafe_allow_html=True)
        sign_in, create_account = st.tabs(["Sign in", "Create account"])
        with sign_in:
            with st.form("login_form"):
                username = st.text_input("Username", autocomplete="username")
                password = st.text_input("Password", type="password", autocomplete="current-password")
                submitted = st.form_submit_button("Sign in", type="primary", use_container_width=True)
            if submitted:
                user = authenticate(username, password)
                if user is None:
                    st.error("That username and password didn't match.")
                else:
                    st.session_state["user"] = user
                    st.rerun()
            st.caption("Starter account: admin / admin123")
        with create_account:
            with st.form("create_account_form"):
                new_username = st.text_input("Choose a username", max_chars=80)
                new_password = st.text_input("Choose a password", type="password")
                submitted = st.form_submit_button("Create account", type="primary", use_container_width=True)
            if submitted:
                try:
                    new_user_id = create_user(new_username, new_password)
                except ValueError as error:
                    st.error(str(error))
                except sqlite3.IntegrityError:
                    st.error("That username is already in use.")
                else:
                    st.session_state["user"] = {"id": new_user_id, "username": new_username.strip()}
                    st.rerun()


def _dashboard(tasks: list[dict[str, Any]]) -> None:
    today = date.today()
    pending = sum(task["status"] == "Pending" for task in tasks)
    in_progress = sum(task["status"] == "In Progress" for task in tasks)
    completed = sum(task["status"] == "Completed" for task in tasks)
    overdue = sum(
        task["status"] != "Completed" and date.fromisoformat(task["due_date"]) < today
        for task in tasks
    )
    st.markdown('<p class="eyebrow">Overview</p>', unsafe_allow_html=True)
    st.title("Your semester at a glance")
    st.markdown('<p class="page-subtitle">A clear view of what is moving and what needs attention.</p>', unsafe_allow_html=True)

    metrics = st.columns(5)
    for column, label, value in zip(
        metrics,
        ("All tasks", "Pending", "In progress", "Completed", "Overdue"),
        (len(tasks), pending, in_progress, completed, overdue),
    ):
        column.metric(label, value)

    st.markdown("### Workload")
    chart, agenda = st.columns([1, 1.2], gap="large")
    with chart:
        st.bar_chart(
            pd.DataFrame(
                {"Tasks": [pending, in_progress, completed]},
                index=["Pending", "In progress", "Completed"],
            ),
            y_label="Tasks",
            horizontal=True,
            height=230,
        )
    with agenda:
        st.markdown("#### Coming up")
        upcoming = [
            task for task in tasks
            if task["status"] != "Completed"
            and today <= date.fromisoformat(task["due_date"]) <= today + timedelta(days=7)
        ]
        upcoming.sort(key=lambda task: task["due_date"])
        if upcoming:
            for task in upcoming[:5]:
                due = date.fromisoformat(task["due_date"])
                st.markdown(
                    f"**{task['title']}** · {task['category']}  \n"
                    f"<span style='color:#68756d'>{due.strftime('%b')} {due.day} · {task['priority']} priority</span>",
                    unsafe_allow_html=True,
                )
                st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
        else:
            st.info("Nothing due in the next seven days.")

    if overdue:
        st.warning(f"{overdue} task{'s are' if overdue != 1 else ' is'} past the due date. Open View tasks to reschedule or complete {'them' if overdue != 1 else 'it'}.")
    st.markdown("### Recently added")
    recent = sorted(tasks, key=lambda task: task["created_at"], reverse=True)[:5]
    if recent:
        st.dataframe(_task_frame(recent), hide_index=True, use_container_width=True)
    else:
        st.info("Your task list is clear. Add your first task to get started.")


def _add_task(user_id: int) -> None:
    st.markdown('<p class="eyebrow">New item</p>', unsafe_allow_html=True)
    st.title("Add a task")
    st.markdown('<p class="page-subtitle">Capture the next thing you need to move forward.</p>', unsafe_allow_html=True)
    with st.form("add_task_form", clear_on_submit=True):
        title = st.text_input("Task name", max_chars=160, placeholder="e.g. Read chapter 4")
        description = st.text_area("Notes", placeholder="Optional details", height=90)
        first, second, third = st.columns(3)
        category = first.selectbox("Category", CATEGORIES)
        priority = second.selectbox("Priority", PRIORITIES, index=1)
        due_date = third.date_input("Due date", value=date.today() + timedelta(days=7))
        status = st.selectbox("Status", STATUSES)
        submitted = st.form_submit_button("Save task", type="primary")
    if submitted:
        try:
            add_task(user_id, title, category, priority, due_date.isoformat(), status, description)
        except ValueError as error:
            st.error(str(error))
        else:
            st.success("Task saved.")
            st.rerun()


def _view_tasks(user_id: int, tasks: list[dict[str, Any]]) -> None:
    st.markdown('<p class="eyebrow">Task list</p>', unsafe_allow_html=True)
    st.title("View tasks")
    st.markdown('<p class="page-subtitle">Filter your workload, then update the details that changed.</p>', unsafe_allow_html=True)
    filter_columns = st.columns(4)
    status_filter = filter_columns[0].selectbox("Status", ("All", *STATUSES))
    priority_filter = filter_columns[1].selectbox("Priority", ("All", *PRIORITIES))
    category_filter = filter_columns[2].selectbox("Category", ("All", *CATEGORIES))
    sort_by = filter_columns[3].selectbox(
        "Sort by", ("Due date", "Priority", "Status", "Category", "Recently added")
    )
    filtered = [
        task for task in tasks
        if (status_filter == "All" or task["status"] == status_filter)
        and (priority_filter == "All" or task["priority"] == priority_filter)
        and (category_filter == "All" or task["category"] == category_filter)
    ]
    if sort_by == "Priority":
        rank = {"High": 0, "Medium": 1, "Low": 2}
        filtered.sort(key=lambda task: (rank[task["priority"]], task["due_date"]))
    elif sort_by == "Status":
        rank = {status: position for position, status in enumerate(STATUSES)}
        filtered.sort(key=lambda task: (rank[task["status"]], task["due_date"]))
    elif sort_by == "Category":
        filtered.sort(key=lambda task: (task["category"], task["due_date"]))
    elif sort_by == "Recently added":
        filtered.sort(key=lambda task: task["created_at"], reverse=True)
    else:
        filtered.sort(key=lambda task: task["due_date"])

    if not filtered:
        st.info("No tasks match those filters.")
        return

    display = _task_frame(filtered)
    def highlight_deadline(row: pd.Series) -> list[str]:
        if row["Deadline"] == "Overdue":
            return ["background-color: #fbe4df; color: #8d3022"] * len(row)
        if row["Deadline"] in ("Due today", "Coming up"):
            return ["background-color: #f0f5d9"] * len(row)
        return [""] * len(row)

    st.dataframe(display.style.apply(highlight_deadline, axis=1), hide_index=True, use_container_width=True)
    st.caption(f"Showing {len(filtered)} of {len(tasks)} tasks. Overdue rows are highlighted in coral.")
    st.markdown("### Update a task")
    selected_id = st.selectbox(
        "Choose task",
        options=[task["id"] for task in filtered],
        format_func=lambda task_id: next(task["title"] for task in filtered if task["id"] == task_id),
        key="selected_task_id",
    )
    selected = next(task for task in filtered if task["id"] == selected_id)
    category_index = CATEGORIES.index(selected["category"])
    priority_index = PRIORITIES.index(selected["priority"])
    status_index = STATUSES.index(selected["status"])
    with st.form(f"edit_task_{selected_id}"):
        edited_title = st.text_input("Task name", selected["title"], max_chars=160)
        edited_description = st.text_area("Notes", selected["description"], height=80)
        first, second, third = st.columns(3)
        edited_category = first.selectbox("Category", CATEGORIES, index=category_index)
        edited_priority = second.selectbox("Priority", PRIORITIES, index=priority_index)
        edited_due = third.date_input("Due date", date.fromisoformat(selected["due_date"]))
        edited_status = st.selectbox("Status", STATUSES, index=status_index)
        save = st.form_submit_button("Save changes", type="primary")
    if save:
        try:
            changed = update_task(
                user_id,
                selected_id,
                edited_title,
                edited_category,
                edited_priority,
                edited_due.isoformat(),
                edited_status,
                edited_description,
            )
        except ValueError as error:
            st.error(str(error))
        else:
            if changed:
                st.success("Task updated.")
                st.rerun()
            st.error("That task is no longer available.")

    quick, danger = st.columns([1, 5])
    with quick:
        if selected["status"] != "Completed" and st.button("Mark complete", key=f"complete_{selected_id}"):
            update_task(
                user_id,
                selected_id,
                selected["title"],
                selected["category"],
                selected["priority"],
                selected["due_date"],
                "Completed",
                selected["description"],
            )
            st.rerun()
        elif selected["status"] == "Completed" and st.button("Reopen task", key=f"reopen_{selected_id}"):
            update_task(
                user_id,
                selected_id,
                selected["title"],
                selected["category"],
                selected["priority"],
                selected["due_date"],
                "Pending",
                selected["description"],
            )
            st.rerun()
    with danger:
        if st.button("Delete task", key=f"delete_{selected_id}"):
            st.session_state["confirm_delete_id"] = selected_id
    if st.session_state.get("confirm_delete_id") == selected_id:
        st.warning(f"Delete **{selected['title']}** permanently?")
        confirm, cancel = st.columns(2)
        if confirm.button("Confirm delete", type="primary", key=f"confirm_{selected_id}"):
            delete_task(user_id, selected_id)
            st.session_state.pop("confirm_delete_id", None)
            st.rerun()
        if cancel.button("Cancel", key=f"cancel_{selected_id}"):
            st.session_state.pop("confirm_delete_id", None)
            st.rerun()


def main() -> None:
    init_db(DEFAULT_DB_PATH)
    if "user" not in st.session_state:
        _show_login()
        return

    user = st.session_state["user"]
    with st.sidebar:
        st.markdown('<div class="login-mark">S.</div>', unsafe_allow_html=True)
        st.markdown("## Studylist")
        st.caption(f"Signed in as **{user['username']}**")
        page = st.radio("Workspace", ("Dashboard", "Add task", "View tasks"), label_visibility="collapsed")
        st.markdown('<div class="section-rule"></div>', unsafe_allow_html=True)
        if st.button("Sign out", use_container_width=True):
            st.session_state.pop("user", None)
            st.rerun()

    tasks = list_tasks(user["id"])
    if page == "Dashboard":
        _dashboard(tasks)
    elif page == "Add task":
        _add_task(user["id"])
    else:
        _view_tasks(user["id"], tasks)


if __name__ == "__main__":
    main()