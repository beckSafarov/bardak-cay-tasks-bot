from datetime import date

import asyncpg

async def fetch_manager_by_telegram_id(conn: asyncpg.Connection, telegram_id: int):
    """Fetch an active manager record using their Telegram user ID."""
    return await conn.fetchrow(
        "SELECT id, full_name, restaurant_id, branch_id FROM managers "
        "WHERE telegram_id = $1 AND is_active = true",
        telegram_id,
    )

async def fetch_pending_tasks_for_manager(
    conn: asyncpg.Connection,
    manager_id: int,
    scheduled_date: date,
):
    """Fetch incomplete task instances for a manager on a specific date."""
    return await conn.fetch(
        """
        SELECT ti.id, ti.scheduled_date, ti.due_at, tt.title, tt.description
        FROM task_instances ti
        JOIN task_templates tt ON ti.template_id = tt.id
        WHERE ti.manager_id = $1
          AND ti.completed = false
          AND ti.scheduled_date = $2
        ORDER BY tt.due_time NULLS LAST, ti.due_at NULLS LAST
        """,
        manager_id,
        scheduled_date,
    )

async def fetch_task_instances_by_manager_today(
    conn: asyncpg.Connection,
    manager_id: int,
):
    """Fetch pending tasks for today for a manager."""
    return await fetch_pending_tasks_for_manager(conn, manager_id, date.today())
