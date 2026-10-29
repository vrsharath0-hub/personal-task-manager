from datetime import date, timedelta

import pytest

from task_manager import (
    add_task,
    authenticate,
    create_user,
    delete_task,
    init_db,
    list_tasks,
    update_task,
)


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "tasks.sqlite3"
    init_db(path)
    return path


def test_default_account_is_database_backed(database):
    assert authenticate("admin", "admin123", database) == {"id": 1, "username": "admin"}
    assert authenticate("admin", "wrong-password", database) is None


def test_tasks_persist_and_are_isolated_by_user(database):
    admin = authenticate("admin", "admin123", database)
    student_id = create_user("student", "student123", database)
    task_id = add_task(
        admin["id"], "Read notes", "Assignment", "High",
        (date.today() + timedelta(days=2)).isoformat(), db_path=database,
    )
    assert len(list_tasks(admin["id"], database)) == 1
    assert list_tasks(student_id, database) == []
    assert update_task(
        student_id, task_id, "Hijack", "Exam", "Low", date.today().isoformat(),
        "Completed", db_path=database,
    ) is False
    assert delete_task(student_id, task_id, database) is False
    assert list_tasks(admin["id"], database)[0]["title"] == "Read notes"


def test_task_crud(database):
    admin_id = authenticate("admin", "admin123", database)["id"]
    due = (date.today() + timedelta(days=1)).isoformat()
    task_id = add_task(
        admin_id, "Draft outline", "Project", "Medium", due,
        description="First pass", db_path=database,
    )
    assert list_tasks(admin_id, database)[0]["description"] == "First pass"
    assert update_task(
        admin_id, task_id, "Final outline", "Project", "High", due,
        "In Progress", "Updated notes", database,
    ) is True
    updated = list_tasks(admin_id, database)[0]
    assert (updated["title"], updated["priority"], updated["status"]) == (
        "Final outline", "High", "In Progress"
    )
    assert delete_task(admin_id, task_id, database) is True
    assert list_tasks(admin_id, database) == []


@pytest.mark.parametrize(
    "title,category,priority,status,due_date",
    [
        ("  ", "Assignment", "High", "Pending", "2030-01-01"),
        ("Task", "Unknown", "High", "Pending", "2030-01-01"),
        ("Task", "Exam", "Urgent", "Pending", "2030-01-01"),
        ("Task", "Exam", "Low", "Blocked", "2030-01-01"),
        ("Task", "Exam", "Low", "Pending", "not-a-date"),
    ],
)
def test_invalid_task_values_are_rejected(database, title, category, priority, status, due_date):
    admin_id = authenticate("admin", "admin123", database)["id"]
    with pytest.raises(ValueError):
        add_task(admin_id, title, category, priority, due_date, status, db_path=database)
