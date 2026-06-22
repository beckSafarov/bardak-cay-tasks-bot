import html
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from aiogram import Router, types
from utils.tasks import (
    mark_task_instance_completed,
    mark_task_instance_incomplete,
    fetch_task_instance,
)
from utils.keyboards import build_status_update_keyboard
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()


def parse_mark_status_payload(callback_data: str) -> Optional[int]:
    parts = callback_data.split(":", 1)
    if len(parts) != 2 or not parts[1].isdigit():
        return None
    return int(parts[1])


async def strike_message_text(message: types.Message, task_instance_id: int = None):
    original_text = message.text or ""
    escaped_text = html.escape(original_text)
    struck_text = f"<s>{escaped_text}</s>"
    await message.edit_text(
        struck_text,
        parse_mode="HTML",
        reply_markup=build_status_update_keyboard(task_instance_id, is_done=True),
    )


async def unstrike_message_text(message: types.Message, task_instance_id: int = None):
    original_text = message.text or ""
    escaped_text = html.escape(original_text)
    unstruck_text = re.sub(
        r"^\s*<s>\s*|\s*</s>\s*$", "", escaped_text, flags=re.IGNORECASE
    )
    await message.edit_text(
        unstruck_text,
        parse_mode="HTML",
        reply_markup=build_status_update_keyboard(task_instance_id, is_done=False),
    )


@router.callback_query(
    lambda callback: bool(callback.data and callback.data.startswith("mark_done:"))
)
async def on_mark_done(callback: types.CallbackQuery, db_pool):
    """Handle inline keyboard callback to mark a task instance completed."""
    if callback.data is None or callback.message is None:
        await callback.answer("Unable to mark task as done.", show_alert=True)
        return

    task_instance_id = parse_mark_status_payload(callback.data)
    if task_instance_id is None:
        await callback.answer("Invalid action.", show_alert=True)
        return

    async with db_pool.acquire() as conn:
        task_instance = await fetch_task_instance(conn, task_instance_id)
        # now = datetime.now(ZoneInfo("Asia/Tashkent"))
        now = datetime.now().astimezone()
        due_at_local = task_instance["due_at"].astimezone(now.tzinfo)
        if due_at_local < now:
            await callback.answer(
                "Cannot mark overdue task as complete", show_alert=True
            )
            return
        else:
            print(f"Task due_at: {task_instance['due_at']}, now: {now}")
            await mark_task_instance_completed(conn, task_instance_id)

    try:
        await strike_message_text(callback.message, task_instance_id)
    except Exception as exc:
        print(
            f"Failed to strike message text for task_instance_id={task_instance_id}: {exc}"
        )
        await callback.answer(f"Failed to mark task as done: {exc}", show_alert=True)
        pass

    await callback.answer("Task marked done ✅")


@router.callback_query(
    lambda callback: bool(callback.data and callback.data.startswith("mark_undone:"))
)
async def on_mark_undone(callback: types.CallbackQuery, db_pool):
    """Handle inline keyboard callback to mark a task instance as incomplete."""
    if callback.data is None or callback.message is None:
        await callback.answer("Unable to mark task as incomplete.", show_alert=True)
        return

    task_instance_id = parse_mark_status_payload(callback.data)
    if task_instance_id is None:
        await callback.answer("Invalid action.", show_alert=True)
        return

    async with db_pool.acquire() as conn:
        task_instance = await fetch_task_instance(conn, task_instance_id)
        # now = datetime.now(ZoneInfo("Asia/Tashkent"))
        now = datetime.now().astimezone()
        due_at_local = task_instance["due_at"].astimezone(now.tzinfo)
        if due_at_local < now:
            await callback.answer(
                "Cannot mark overdue task as incomplete", show_alert=True
            )
            return
        else:
            print(f"Task due_at: {task_instance['due_at']}, now: {now}")
            await mark_task_instance_incomplete(conn, task_instance_id)

    try:
        await unstrike_message_text(callback.message, task_instance_id)
    except Exception:
        pass

    await callback.answer("Task marked incomplete ❌")
