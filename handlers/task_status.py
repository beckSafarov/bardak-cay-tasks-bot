import html
import logging
import re
from datetime import datetime, timezone
from typing import Optional
from aiogram import F, Router, types
from aiogram.fsm.state import State, StatesGroup
from utils.tasks import (
    mark_task_instance_completed,
    mark_task_instance_incomplete,
    add_note_to_task_instance,
    fetch_task_instance,
)
from utils.keyboards import build_status_update_keyboard
from utils.index import get_labels
from zoneinfo import ZoneInfo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
router = Router()
labels = get_labels().get("task_status", {})


class TaskForm(StatesGroup):
    waiting_for_note = State()


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
        await callback.answer(labels["unable_to_mark_done"], show_alert=True)
        return

    task_instance_id = parse_mark_status_payload(callback.data)
    if task_instance_id is None:
        await callback.answer(labels["invalid_action"], show_alert=True)
        return

    async with db_pool.acquire() as conn:
        task_instance = await fetch_task_instance(conn, task_instance_id)
        # now = datetime.now(ZoneInfo("Asia/Tashkent"))
        now = datetime.now().astimezone()
        due_at_local = task_instance["due_at"].astimezone(now.tzinfo)
        if due_at_local < now:
            await callback.answer(
                labels["cannot_mark_overdue_complete"], show_alert=True
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
        await callback.answer(
            labels["failed_to_mark_done"].replace("<error>", str(exc)),
            show_alert=True,
        )
        pass

    await callback.answer(labels["task_marked_done"])


@router.callback_query(
    lambda callback: bool(callback.data and callback.data.startswith("mark_undone:"))
)
async def on_mark_undone(callback: types.CallbackQuery, db_pool):
    """Handle inline keyboard callback to mark a task instance as incomplete."""
    if callback.data is None or callback.message is None:
        await callback.answer(labels["unable_to_mark_undone"], show_alert=True)
        return

    task_instance_id = parse_mark_status_payload(callback.data)
    if task_instance_id is None:
        await callback.answer(labels["invalid_action"], show_alert=True)
        return

    async with db_pool.acquire() as conn:
        task_instance = await fetch_task_instance(conn, task_instance_id)
        # now = datetime.now(ZoneInfo("Asia/Tashkent"))
        now = datetime.now().astimezone()
        due_at_local = task_instance["due_at"].astimezone(now.tzinfo)
        if due_at_local < now:
            await callback.answer(
                labels["cannot_mark_overdue_incomplete"], show_alert=True
            )
            return
        else:
            print(f"Task due_at: {task_instance['due_at']}, now: {now}")
            await mark_task_instance_incomplete(conn, task_instance_id)

    try:
        await unstrike_message_text(callback.message, task_instance_id)
    except Exception:
        pass

    await callback.answer(labels["task_marked_undone"])


from aiogram import Router, types
from aiogram.fsm.context import FSMContext

router = Router()


@router.callback_query(F.data.startswith("add_note:"))
async def handle_add_note_click(callback: types.CallbackQuery, state: FSMContext):
    # 1. Extract the task instance ID from the callback data
    task_instance_id = int(callback.data.split(":")[1])
    task_instance_title = callback.data.split(":")[2]

    # 2. Set the current user's state to waiting_for_note
    await state.set_state(TaskForm.waiting_for_note)

    # 3. Store the task_instance_id in FSM context so we don't lose it
    await state.update_data(current_task_id=task_instance_id)

    # 4. Notify the user to type their text
    await callback.message.answer(
        labels["type_note_prompt"].replace(
            "<task>", f"({task_instance_id}. {task_instance_title})"
        )
    )

    # 5. Acknowledge the callback click so the loading wheel stops spinning
    await callback.answer()


@router.message(TaskForm.waiting_for_note)
async def process_note_text_input(message: types.Message, state: FSMContext, db_pool):
    # 1. Get the text the user sent as their note
    note_text = message.text.strip()

    if not note_text:
        await message.answer(labels["note_cannot_be_empty"])
        return

    # 2. Retrieve the task ID we saved earlier in Step 2
    user_data = await state.get_data()
    task_instance_id = user_data.get("current_task_id")
    # task_title = user_data.get("current_task_title")

    # 3. Update your database with the note
    await add_note_to_task_instance(db_pool, note_text, task_instance_id)

    # 4. Confirm to the user that it was saved successfully
    await message.answer(
        labels["note_added"].replace("<task_id>", str(task_instance_id))
    )

    # 5. CRITICAL: Clear the state so they can use normal bot commands again
    await state.clear()
