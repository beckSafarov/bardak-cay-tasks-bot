from datetime import date

import asyncpg


async def fetch_personnel_by_phone(conn: asyncpg.Connection, phone_number: str):
    """Fetch an active personnel record using their phone number."""
    return await conn.fetchrow(
        "SELECT id, full_name, restaurant_id, branch_id FROM personnel "
        "WHERE phone_number = $1 AND is_active = true",
        phone_number,
    )


async def set_personnel_telegram_id_by_phone(
    conn: asyncpg.Connection,
    phone_number: str,
    telegram_id: int,
) -> None:
    """Set the Telegram ID for a personnel member based on their phone number."""

    await conn.execute(
        "UPDATE personnel SET telegram_id = $1 WHERE phone_number = $2",
        telegram_id,
        phone_number,
    )


async def fetch_personnel_by_telegram_id(conn: asyncpg.Connection, telegram_id: int):
    """Fetch an active personnel record using their Telegram user ID."""
    return await conn.fetchrow(
        "SELECT id, full_name, restaurant_id, branch_id FROM personnel "
        "WHERE telegram_id = $1 AND is_active = true",
        telegram_id,
    )


async def fetch_pending_tasks_for_personnel(
    conn: asyncpg.Connection,
    personnel_id: int,
    scheduled_date: date,
):
    """Fetch incomplete task instances for a personnel member on a specific date."""

    return await conn.fetch(
        """
        SELECT ti.id, ti.scheduled_date, ti.due_at, tt.title, tt.description
        FROM task_instances ti
        JOIN task_templates tt ON ti.template_id = tt.id
        WHERE ti.personnel_id = $1
          AND ti.completed = false
          AND ti.scheduled_date = $2
        ORDER BY tt.due_time NULLS LAST, ti.due_at NULLS LAST
        """,
        personnel_id,
        scheduled_date,
    )


async def fetch_task_instances_by_personnel_today(
    conn: asyncpg.Connection,
    personnel_id: int,
):
    """Fetch pending tasks for today for a personnel member."""

    return await fetch_pending_tasks_for_personnel(conn, personnel_id, date.today())
