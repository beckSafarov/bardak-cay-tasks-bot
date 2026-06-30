from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from .index import get_trunc_text
from utils.index import get_labels

def build_status_update_keyboard(
    task_instance_id: int, task_instance_title: str, is_done: bool
) -> InlineKeyboardMarkup:
    """Build the inline keyboard for marking a task done/undone."""
    labels = get_labels().get("task_status", {})
    status_update_label = (
        labels.get("mark_undone") if is_done else labels.get("mark_done")
    )
    status_update_callback_data_label = f"mark_undone:" if is_done else f"mark_done:"
    title = get_trunc_text(task_instance_title, 16)
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=status_update_label,
                    callback_data=status_update_callback_data_label
                    + str(task_instance_id),
                ),
                InlineKeyboardButton(
                    text=labels.get("add_note"),
                    callback_data=f"add_note:{str(task_instance_id)}:{title}",
                ),
            ]
        ]
    )
