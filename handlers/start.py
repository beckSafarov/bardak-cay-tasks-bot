from datetime import date
import logging
from sched import scheduler
from aiogram import Bot, Router, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode  # Ensure this import is present
from utils.personnel import (
    fetch_personnel_by_phone,
    fetch_personnel_by_telegram_id,
)
from utils.set_and_send_checklist import set_and_send_checklists
from utils.personnel import (
    fetch_personnel_by_telegram_id,
    set_personnel_telegram_id_by_phone,
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from utils.stats import fetch_task_statistics
from utils.index import get_trunc_text, get_labels

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = Router()
labels = get_labels().get("main", {})

async def fetch_personnel(message: types.Message, db_pool):
    async with db_pool.acquire() as conn:
        return await fetch_personnel_by_telegram_id(conn, message.from_user.id)


async def require_personnel(message: types.Message, db_pool):
    personnel = await fetch_personnel(message, db_pool)
    if not personnel:
        await message.answer(labels["access_denied_personnel_not_found"])
    return personnel


@router.message(Command("start"))
async def cmd_start(message: types.Message, db_pool, bot: Bot):
    """Handle /start command and schedule tasks for registered personnel."""

    # Create a keyboard builder
    builder = ReplyKeyboardBuilder()

    # Add a special button that securely requests their contact info
    builder.button(text=labels["share_phone"], request_contact=True)

    welcome_text = "\n".join(labels["welcome_message"])

    await message.answer(
        welcome_text,
        reply_markup=builder.as_markup(resize_keyboard=True, one_time_keyboard=True),
    )


@router.message(F.contact)
async def handle_contact(message: types.Message, db_pool):
    """
    Receive the secure phone number from Telegram and authenticate the manager.
    """
    contact = message.contact

    # Security Check: Ensure the shared contact actually belongs to the user clicking the button
    if contact.user_id != message.from_user.id:
        await message.answer(
            labels["auth_failed"],
            reply_markup=types.ReplyKeyboardRemove(),  # Clears the button
        )
        return

    # Clean the phone number (Telegram usually sends it with a leading '+' or country code)
    phone_number = contact.phone_number.strip().replace("+", "")

    # Look up the personnel in your database by phone number
    personnel = await fetch_personnel_by_phone(db_pool, phone_number)

    if personnel:
        # Optional: Save their telegram_id to the database now so you can push scheduled tasks to them later
        await set_personnel_telegram_id_by_phone(
            db_pool, phone_number, message.from_user.id
        )

        await message.answer(
            labels["auth_success"].replace("<user>", personnel["full_name"])
            + "\n"
            + labels["tasks_command_suggestion"],
            reply_markup=types.ReplyKeyboardRemove(),  # Successfully removes the share button
        )
    else:
        await message.answer(
            labels["access_denied"],
            reply_markup=types.ReplyKeyboardRemove(),
        )


@router.message(Command("tasks"))
async def cmd_tasks(message: types.Message, db_pool, bot: Bot):
    """List pending tasks for the personnel."""

    personnel = await require_personnel(message, db_pool)
    if not personnel:
        return

    await message.answer(labels["fetching_tasks_today"])
    await set_and_send_checklists(db_pool, bot)


@router.message(Command("stats"))
async def cmd_stats(message: types.Message, db_pool, bot: Bot):
    """List task statistics for the personnel as a clean Markdown table."""

    personnel = await require_personnel(message, db_pool)
    if not personnel:
        return

    # 1. Fetch data
    stats = await fetch_task_statistics(
        db_pool, personnel["id"], date.today().month, date.today().year
    )

    if not stats:
        await message.answer(labels["no_stats_found"])
        return

    # 2. Build the Markdown table headers
    # We use left-aligned strings with fixed widths for a structured look
    table_lines = [
        "```",  # Start monospaced code block
        f"{labels['stats_table_header_title']:<16} | {labels['stats_table_header_total']:<3} | {labels['stats_table_header_completed']:<3} | {labels['stats_table_header_percentage']:<4}",
        "-" * 35,  # Divider line
    ]

    # 3. Populate rows dynamically
    for stat in stats:
        # Truncate long titles to keep the table structure rigid and clean
        # title = (
        #     stat["task_title"][:14] + ".."
        #     if len(stat["task_title"]) > 16
        #     else stat["task_title"]
        # )
        title = get_trunc_text(stat["task_title"], 16)
        tot = stat["total_instances"]
        cmp = stat["completed_tasks"]
        pct = f"{int(stat['completion_percentage'])}%"

        table_lines.append(f"{title:<16} | {tot:<3} | {cmp:<3} | {pct:<4}")

    table_lines.append("```")  # End monospaced code block

    # 4. Join lines and send as a single message
    final_message = "\n".join(table_lines)

    await message.answer(
        labels["user_stats_this_month"].replace("<final_message>", final_message),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
