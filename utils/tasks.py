from datetime import date

import asyncpg


async def fetch_all_task_templates(conn: asyncpg.Connection):
    """Fetch all task templates."""
    return await conn.fetch("SELECT * FROM task_templates")


async def fetch_all_task_instances(conn: asyncpg.Connection):
    """Fetch all task instances."""
    return await conn.fetch("SELECT * FROM task_instances")


async def fetch_tasks_template_by_user(conn: asyncpg.Connection, telegram_id: int):
    """Fetch task templates for a manager by Telegram ID."""
    return await conn.fetch(
        """
        SELECT tt.*
        FROM task_templates tt
        JOIN managers m
          ON m.restaurant_id = tt.restaurant_id
         AND m.branch_id = tt.branch_id
        WHERE m.telegram_id = $1
          AND m.is_active = TRUE
        """,
        telegram_id,
    )


async def create_task_instance(
    conn: asyncpg.Connection,
    restaurant_id: int,
    branch_id: int,
    manager_id: int,
    template_id: int,
    scheduled_date: date,
    due_at,
    note: str | None = None,
):
    """Create a new task instance row from the task template details."""
    return await conn.fetchrow(
        """
        INSERT INTO task_instances (
            restaurant_id,
            branch_id,
            manager_id,
            template_id,
            scheduled_date,
            due_at,
            note
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        restaurant_id,
        branch_id,
        manager_id,
        template_id,
        scheduled_date,
        due_at,
        note,
    )
