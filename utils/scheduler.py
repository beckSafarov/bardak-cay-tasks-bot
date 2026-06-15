from datetime import datetime, timedelta, timezone
from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import asyncpg
from .tasks import (
    create_task_instance,
    fetch_all_task_templates,
    fetch_all_task_instances,
)
from .keyboards import build_mark_done_keyboard, build_mark_undone_keyboard

def format_due_at_relative(due_at: datetime, now: datetime) -> str:
    """Return a humanized relative due date string."""
    if due_at.tzinfo is None:
        due_at = due_at.replace(tzinfo=timezone.utc)

    today = now.date()
    due_date = due_at.date()
    delta = due_date - today
    time_str = due_at.strftime("%H:%M")

    if delta.days == 0:
        return f"today at {time_str}"
    if delta.days == 1:
        return f"tomorrow at {time_str}"
    if 1 < delta.days < 7:
        return f"in {delta.days} days at {time_str}"
    return f"on {due_at.strftime('%Y-%m-%d')} at {time_str}"


def compute_next_due_at(frequency: str, now: datetime) -> datetime | None:
    """Compute the next due date based on frequency."""
    if frequency == 'daily':
        next_day = now + timedelta(days=1)
        return datetime(next_day.year, next_day.month, next_day.day, 2, 0, tzinfo=timezone.utc)

    if frequency == 'weekly':
        days_ahead = 7 - now.weekday()
        if days_ahead == 0:
            days_ahead = 7
        next_week = now + timedelta(days=days_ahead)
        return datetime(next_week.year, next_week.month, next_week.day, 2, 0, tzinfo=timezone.utc)

    if frequency == 'monthly':
        if now.month == 12:
            return datetime(now.year + 1, 1, 1, 2, 0, tzinfo=timezone.utc)
        return datetime(now.year, now.month + 1, 1, 2, 0, tzinfo=timezone.utc)

    return None


async def get_tasks_to_create(conn):
    """Return available templates and existing task instances for debugging/testing."""
    all_task_templates = await fetch_all_task_templates(conn)
    all_task_instances = await fetch_all_task_instances(conn)

    return {
        "templates": all_task_templates,
        "instances": all_task_instances,
    }


async def fetch_active_templates_with_managers(conn: asyncpg.Connection):
    """Fetch active task templates joined to active managers."""
    return await conn.fetch(
        """
        SELECT
            tt.id AS template_id,
            tt.restaurant_id,
            tt.branch_id,
            tt.title,
            tt.description,
            tt.frequency,
            m.id AS manager_id,
            m.telegram_id
        FROM task_templates tt
        JOIN managers m
          ON tt.branch_id = m.branch_id
         AND tt.restaurant_id = m.restaurant_id
        WHERE tt.is_active = true
          AND m.is_active = true
        """
    )


async def fetch_latest_task_instance(
    conn: asyncpg.Connection,
    template_id: int,
    manager_id: int,
):
    """Fetch the most recent task instance for a given template and manager."""
    return await conn.fetchrow(
        """
        SELECT due_at, completed
        FROM task_instances
        WHERE template_id = $1 AND manager_id = $2
        ORDER BY due_at DESC NULLS LAST
        LIMIT 1
        """,
        template_id,
        manager_id,
    )


def should_create_task_instance(
    latest_instance: asyncpg.Record | None,
    now: datetime,
) -> tuple[bool, datetime | None]:
    """Decide whether a new task instance should be created."""
    if latest_instance is None:
        return True, None

    max_due_at = latest_instance['due_at']
    completed = latest_instance['completed']

    if max_due_at is None:
        return True, None

    if max_due_at < now:
        return True, None

    if max_due_at >= now and not completed:
        return True, max_due_at

    return False, None


async def create_scheduled_task_instance(
    conn: asyncpg.Connection,
    record: asyncpg.Record,
    due_at: datetime,
    scheduled_date: datetime.date,
) -> asyncpg.Record:
    """Insert and return a new task instance for the resolved template/manager pair."""
    return await create_task_instance(
        conn,
        record["restaurant_id"],
        record["branch_id"],
        record["manager_id"],
        record["template_id"],
        scheduled_date,
        due_at,
    )


def build_task_message(record: asyncpg.Record, due_at: datetime, now: datetime) -> str:
    """Build the message text for the manager."""
    description = record['description'] or 'No description'
    relative_due = format_due_at_relative(due_at, now)
    return (
        f"☑️ Task title: {record['title']}\n"
        f"📃 Description: {description}\n"
        f"⏰ Due at: {relative_due}"
    )


async def schedule_tasks_for_managers(db_pool: asyncpg.Pool, bot: Bot):
    """Create and send effective task instances to active managers."""
    async with db_pool.acquire() as conn:
        active_templates = await fetch_active_templates_with_managers(conn)
        now = datetime.now(timezone.utc)
        scheduled_date = now.date()
        tasks_to_notify = []

        for record in active_templates:
            latest_instance = await fetch_latest_task_instance(
                conn,
                record['template_id'],
                record['manager_id'],
            )

            should_create, due_at = should_create_task_instance(latest_instance, now)
            if not should_create:
                continue

            if due_at is None:
                due_at = compute_next_due_at(record['frequency'], now)
            if due_at is None:
                continue

            task_instance = await create_scheduled_task_instance(
                conn,
                record,
                due_at,
                scheduled_date,
            )
            tasks_to_notify.append((record, due_at, task_instance["id"]))

        for record, due_at, task_instance_id in tasks_to_notify:
            try:
                await bot.send_message(
                    record["telegram_id"],
                    build_task_message(record, due_at, now),
                    reply_markup=build_mark_done_keyboard(task_instance_id),
                )
            except Exception as exc:
                print(f"Failed to send message to {record['telegram_id']}: {exc}")
