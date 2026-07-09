from uuid import uuid4

from flask import Blueprint, current_app, jsonify, request

from api.middleware.auth import login_required
from src.sqlite_store import connect


tasks_bp = Blueprint("tasks", __name__)

TASK_SELECT = """
SELECT
    tasks.id,
    tasks.title,
    tasks.description,
    tasks.status,
    tasks.priority,
    tasks.assigned_to,
    tasks.due_date,
    tasks.case_id,
    cases.contract_number AS case_contract_number,
    cases.customer_info AS case_customer_info,
    cases.owner_name AS case_owner_name,
    cases.dia_chi_thua_dat AS case_address,
    cases.source AS case_source,
    cases.personal_note AS case_note
FROM tasks
LEFT JOIN cases ON cases.id = tasks.case_id
"""

UPDATABLE_TASK_COLUMNS = {
    "title",
    "description",
    "status",
    "priority",
    "assigned_to",
    "due_date",
    "case_id",
}


def get_task(conn, task_id):
    row = conn.execute(
        f"{TASK_SELECT} WHERE tasks.id = ?",
        (task_id,),
    ).fetchone()
    return dict(row) if row else None


@tasks_bp.route("", methods=["GET"])
@login_required
def list_tasks_endpoint():
    db = current_app.config["SQLITE_DATABASE"]
    case_id = request.args.get("case_id")
    sql = TASK_SELECT
    params = {}
    if case_id:
        sql += " WHERE tasks.case_id = :case_id"
        params["case_id"] = case_id
    sql += " ORDER BY tasks.due_date IS NULL, tasks.due_date ASC, tasks.title ASC"

    with connect(db) as conn:
        rows = conn.execute(sql, params).fetchall()
        return jsonify({"items": [dict(row) for row in rows]})


@tasks_bp.route("", methods=["POST"])
@login_required
def create_task_endpoint():
    db = current_app.config["SQLITE_DATABASE"]
    data = request.get_json() or {}
    title = str(data.get("title") or "").strip()
    if not title:
        return jsonify({"error": "Tieu de cong viec la bat buoc"}), 400

    task_id = str(uuid4())
    reminder = data.get("reminder") or {}
    remind_at = reminder.get("remind_at") or data.get("remind_at")
    channels = reminder.get("channels") or data.get("channels") or "telegram"

    with connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            INSERT INTO tasks (
                id, title, description, status, priority,
                assigned_to, due_date, case_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                title,
                data.get("description"),
                data.get("status") or "todo",
                data.get("priority"),
                data.get("assigned_to"),
                data.get("due_date"),
                data.get("case_id"),
            ),
        )
        if remind_at:
            conn.execute(
                """
                INSERT INTO reminders (task_id, remind_at, channels)
                VALUES (?, ?, ?)
                """,
                (task_id, remind_at, channels),
            )
        task = get_task(conn, task_id)

    return jsonify(task), 201


@tasks_bp.route("/<task_id>", methods=["PUT"])
@login_required
def update_task_endpoint(task_id):
    db = current_app.config["SQLITE_DATABASE"]
    data = request.get_json() or {}
    updates = {key: data[key] for key in UPDATABLE_TASK_COLUMNS if key in data}

    if "title" in updates:
        updates["title"] = str(updates["title"] or "").strip()
        if not updates["title"]:
            return jsonify({"error": "Tieu de cong viec la bat buoc"}), 400

    if not updates:
        return jsonify({"error": "Khong co du lieu cap nhat"}), 400

    assignments = ", ".join(f"{key} = :{key}" for key in updates)
    params = {**updates, "id": task_id}

    with connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.execute(
            f"UPDATE tasks SET {assignments} WHERE id = :id",
            params,
        )
        if cursor.rowcount == 0:
            return jsonify({"error": "Khong tim thay cong viec"}), 404

        reminder = data.get("reminder") or {}
        remind_at = reminder.get("remind_at")
        channels = reminder.get("channels") or "telegram"
        if remind_at:
            conn.execute(
                "DELETE FROM reminders WHERE task_id = ? AND is_sent = 0",
                (task_id,),
            )
            conn.execute(
                """
                INSERT INTO reminders (task_id, remind_at, channels)
                VALUES (?, ?, ?)
                """,
                (task_id, remind_at, channels),
            )
        task = get_task(conn, task_id)

    return jsonify(task)


@tasks_bp.route("/<task_id>", methods=["DELETE"])
@login_required
def delete_task_endpoint(task_id):
    db = current_app.config["SQLITE_DATABASE"]

    with connect(db) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cursor.rowcount == 0:
            return jsonify({"error": "Khong tim thay cong viec"}), 404

    return jsonify({"deleted": True})
