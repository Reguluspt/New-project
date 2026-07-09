from __future__ import annotations

import argparse
import html
import json
import logging
import os
import sqlite3
import time
import urllib.parse
import urllib.request
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - production requirements include python-dotenv
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "cases.db"
LOG_PATH = PROJECT_ROOT / "logs" / "reminders.log"


def _logger() -> logging.Logger:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("reminder_service")
    if not logger.handlers:
        handler = logging.FileHandler(LOG_PATH, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    return logger


def _load_env() -> None:
    if load_dotenv is not None:
        load_dotenv(PROJECT_ROOT / "API.env")


def _send_telegram_message(text: str) -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not bot_token or not chat_id:
        raise RuntimeError("Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID")

    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=payload,
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        description = result.get("description", "Telegram API returned ok=false")
        raise RuntimeError(description)


def _format_reminder_message(row: sqlite3.Row) -> str:
    title = html.escape(row["title"] or "Cong viec chua co tieu de")
    description = html.escape(row["description"] or "")
    due_date = html.escape(row["due_date"] or "Chua co han")
    assigned_to = html.escape(row["assigned_to"] or "Chua phan cong")
    priority = html.escape(row["priority"] or "Chua dat")
    status = html.escape(row["status"] or "")

    parts = [
        "<b>Nhac viec</b>",
        f"<b>{title}</b>",
        f"Trang thai: {status}",
        f"Uu tien: {priority}",
        f"Nguoi phu trach: {assigned_to}",
        f"Han xu ly: {due_date}",
    ]
    if description:
        parts.append(f"Mo ta: {description}")
    if row["case_id"] is not None:
        parts.append(f"Ho so lien quan: #{row['case_id']}")
    return "\n".join(parts)


def check_and_send_reminders(db_path: str | Path = DEFAULT_DB_PATH) -> int:
    _load_env()
    logger = _logger()
    sent_count = 0

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                reminders.id AS reminder_id,
                reminders.channels,
                reminders.remind_at,
                tasks.id AS task_id,
                tasks.title,
                tasks.description,
                tasks.status,
                tasks.priority,
                tasks.assigned_to,
                tasks.due_date,
                tasks.case_id
            FROM reminders
            JOIN tasks ON tasks.id = reminders.task_id
            WHERE reminders.remind_at <= CURRENT_TIMESTAMP
              AND reminders.is_sent = 0
            ORDER BY reminders.remind_at ASC, reminders.id ASC
            """
        ).fetchall()

        for row in rows:
            channels = {item.strip().lower() for item in (row["channels"] or "").split(",")}
            if "telegram" not in channels:
                continue

            _send_telegram_message(_format_reminder_message(row))
            conn.execute(
                "UPDATE reminders SET is_sent = 1 WHERE id = ?",
                (row["reminder_id"],),
            )
            conn.commit()
            sent_count += 1
            logger.info("Sent reminder id=%s task_id=%s", row["reminder_id"], row["task_id"])

    return sent_count


def run_reminder_worker(interval_seconds: int = 60) -> None:
    logger = _logger()
    logger.info("Reminder worker started interval_seconds=%s", interval_seconds)
    while True:
        try:
            sent_count = check_and_send_reminders()
            if sent_count:
                logger.info("Reminder worker sent_count=%s", sent_count)
        except Exception:
            logger.exception("Reminder worker iteration failed")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=int, default=60)
    args = parser.parse_args()

    if args.loop:
        run_reminder_worker(args.interval)
    else:
        print(check_and_send_reminders())
