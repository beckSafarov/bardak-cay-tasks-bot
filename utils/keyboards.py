from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def build_mark_undone_keyboard(task_instance_id: int) -> InlineKeyboardMarkup:
    """Build the inline keyboard for marking a task undone."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Mark Undone",
                    callback_data=f"mark_undone:{task_instance_id}",
                )
            ]
        ]
    )
    
def build_mark_done_keyboard(task_instance_id: int) -> InlineKeyboardMarkup:
    """Build the inline keyboard for marking a task done."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Mark Done",
                    callback_data=f"mark_done:{task_instance_id}",
                )
            ]
        ]
    )
