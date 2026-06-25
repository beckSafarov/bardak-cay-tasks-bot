from datetime import date
import asyncpg

async def fetch_task_statistics(
    conn: asyncpg.Connection,
    personnel_id: int,
    date_month: date,
    date_year: date
):
    """Fetch task statistics for a personnel member within a date range."""

    return await conn.fetch(
        """
        select 
          tt.id as task_id, 
          tt.title as task_title,
          COUNT(ti.id) AS total_instances,
          COUNT(CASE WHEN ti.completed = true THEN 1 END) AS completed_tasks,
          (COUNT(CASE WHEN ti.completed = true THEN 1 END) * 100) / COUNT(ti.id)  AS completion_percentage
        from task_templates tt
        join task_instances ti on tt.id = ti.template_id
        WHERE ti.personnel_id = $1
        AND extract(month from ti.scheduled_date) = $2
        AND extract(year from ti.scheduled_date) = $3
        group by tt.id, tt.title
        order by tt.id
        """,
        personnel_id,
        date_month,
        date_year,
    )
