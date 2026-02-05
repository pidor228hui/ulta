import asyncio
import os
import vk_api
from dotenv import load_dotenv
from db import get_prefixes, add_prefix, get_last_message_id, set_last_message_id
from commands import COMMANDS
from utils import vk_send
import traceback
# ------------------------ Загрузка ALLOWED_USERS ------------------------
load_dotenv("config/.env")
ALLOWED_USERS = set(int(x) for x in os.getenv("ALLOWED_USERS", "").split(",") if x)

# ------------------------ Worker для одного токена ------------------------
async def bot_worker(token, all_tokens):
    vk_session = vk_api.VkApi(token=token)
    vk = vk_session.get_api()
    print(f"[Worker] Запущен для токена {token[:8]}")

    # проверка и добавление дефолтного префикса
    prefixes = await get_prefixes(token)
    if not prefixes:
        await add_prefix(token, "!")  # дефолтный префикс

    last_ids = {}  # словарь для хранения последних msg_id по peer_id

    while True:
        try:
            dialogs = vk.messages.getConversations(count=5)
            for item in dialogs["items"]:
                msg = item["last_message"]

                # ------------------------ Игнорируем невалидные сообщения ------------------------
                if "text" not in msg or msg.get("out", 0) != 1:  # только входящие
                    continue
                if msg["from_id"] not in ALLOWED_USERS:
                    continue

                peer_id = msg["peer_id"]
                msg_id = msg["id"]

                # ------------------------ Проверка последнего сообщения ------------------------
                last_id = await get_last_message_id(token, peer_id)
                if last_id == msg_id:
                    continue
                await set_last_message_id(token, peer_id, msg_id)

                text = msg["text"].strip()
                if not text:
                    continue

                # ------------------------ Определяем префикс и команду ------------------------
                prefixes = await get_prefixes(token)

                text_lower = text.lower()
                used_prefix = None
                real_prefix_len = 0

                for p in prefixes:
                    if text_lower.startswith(p.lower()):
                        used_prefix = p
                        real_prefix_len = len(p)
                        break

                if not used_prefix:
                    continue  # сообщение не начинается с префикса

                cmd_name = text[real_prefix_len:].split()[0].lower()

                if cmd_name in COMMANDS:
                    ctx = {
                        "vk": vk,
                        "peer_id": peer_id,
                        "from_id": msg["from_id"],
                        "text": text,
                        "reply": msg.get("reply_message"),
                        "token": token,
                        "bot_tokens": all_tokens  # список всех токенов
                    }
                    try:
                        await COMMANDS[cmd_name](ctx)
                    except Exception as e:
                        print(f"[Worker {token[:8]} error] Ошибка в команде {cmd_name}: {e}")
                        traceback.print_exc()

            await asyncio.sleep(1)  # пауза между циклами
        except Exception as e:
            print(f"[Worker {token[:8]} error]: {e}")
            await asyncio.sleep(1)

# ------------------------ Главная функция ------------------------
async def main():
    TOKENS = [
        "тут_твой_токен_страницы1",
        "тут_твой_токен_страницы2"
        # добавляй сколько угодно токенов
    ]

    tasks = []
    for token in TOKENS:
        tasks.append(asyncio.create_task(bot_worker(token, TOKENS)))  # <-- передаем список всех токенов

    await asyncio.gather(*tasks)  # запускаем воркеры параллельно

# ------------------------ Запуск ------------------------
if __name__ == "__main__":
    asyncio.run(main())

