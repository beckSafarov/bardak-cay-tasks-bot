from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_status_update_keyboard(
    task_instance_id: int, is_done: bool
) -> InlineKeyboardMarkup:
    """Build the inline keyboard for marking a task done/undone."""
    text = "Mark Undone" if is_done else "Mark Done"
    callback_data_label = f"mark_undone:" if is_done else f"mark_done:"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text,
                    callback_data=callback_data_label + str(task_instance_id),
                )
            ]
        ]
    )
