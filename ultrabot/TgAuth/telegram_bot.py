import os
import vk_api
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from db import store_vk_token


load_dotenv("config/.env")


async def connect_vk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if message is None:
        return

    if not context.args:
        await message.reply_text("❗ Используй: /connect_vk <VK_токен>")
        return

    vk_token = context.args[0].strip()
    if not vk_token:
        await message.reply_text("❗ Используй: /connect_vk <VK_токен>")
        return

    try:
        vk_session = vk_api.VkApi(token=vk_token)
        vk = vk_session.get_api()
        user_info = vk.users.get()[0]
        vk_user_id = user_info["id"]
    except Exception:
        await message.reply_text("❌ Не удалось проверить VK токен.")
        return

    telegram_user_id = message.from_user.id if message.from_user else 0
    await store_vk_token(vk_user_id, telegram_user_id, vk_token)
    await message.reply_text(
        f"✅ VK токен привязан. VK user_id: {vk_user_id}."
    )


def main() -> None:
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set")

    application = ApplicationBuilder().token(telegram_token).build()
    application.add_handler(CommandHandler("connect_vk", connect_vk))
    application.run_polling()


if __name__ == "__main__":
    main()
