from datetime import date

import asyncpg


async def fetch_all_task_templates(conn: asyncpg.Connection):
    """Fetch all task templates."""
    return await conn.fetch("SELECT * FROM task_templates")


async def fetch_all_task_instances(conn: asyncpg.Connection):
    """Fetch all task instances."""
    return await conn.fetch("SELECT * FROM task_instances")


async def fetch_tasks_template_by_user(conn: asyncpg.Connection, telegram_id: int):
    """Fetch task templates for a personnel by Telegram ID."""

    return await conn.fetch(
        """
        SELECT tt.*
        FROM task_templates tt
        JOIN personnel p
          ON p.restaurant_id = tt.restaurant_id
         AND p.branch_id = tt.branch_id
        WHERE p.telegram_id = $1
          AND p.is_active = TRUE
        """,
        telegram_id,
    )


async def create_task_instance(
    conn: asyncpg.Connection,
    restaurant_id: int,
    branch_id: int,
    personnel_id: int,
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
            personnel_id,
            template_id,
            scheduled_date,
            due_at,
            note
        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
        RETURNING *
        """,
        restaurant_id,
        branch_id,
        personnel_id,
        template_id,
        scheduled_date,
        due_at,
        note,
    )


async def fetch_task_instance(
    conn: asyncpg.Connection,
    task_instance_id: int,
) -> asyncpg.Record:
    """Fetch a specific task instance by ID."""
    return await conn.fetchrow(
        "SELECT * FROM task_instances WHERE id = $1",
        task_instance_id,
    )


async def mark_task_instance_incomplete(
    conn: asyncpg.Connection,
    task_instance_id: int,
) -> str:
    """Mark a task instance as incomplete."""
    return await conn.execute(
        """
        UPDATE task_instances
        SET completed = false,
            completed_at = null
        WHERE id = $1
        """,
        task_instance_id,
    )


async def mark_task_instance_completed(
    conn: asyncpg.Connection,
    task_instance_id: int,
) -> str:
    """Mark a task instance as completed."""
    return await conn.execute(
        """
        UPDATE task_instances
        SET completed = true,
            completed_at = now()
        WHERE id = $1
        """,
        task_instance_id,
    )


async def add_note_to_task_instance(
    conn: asyncpg.Connection,
    note: str,
    task_instance_id: int,
) -> str:
    """Mark a task instance as incomplete."""
    return await conn.execute(
        """
        UPDATE task_instances
        SET note = $1
        WHERE id = $2
        """,
        note,
        task_instance_id,
    )
