import datetime
import time
import wikipedia
import psutil
import sys
import os
from db import get_prefixes, add_prefix, remove_prefix, get_message_count
from utils import vk_send

BOT_START_TIME = time.perf_counter()
ADMIN_TOKENS = [""]
wikipedia.set_lang("ru")
COMMANDS = {}

# ------------------------ Декоратор ------------------------
def command(name):
    def wrapper(func):
        COMMANDS[name] = func
        return func
    return wrapper

# ------------------------ !help ------------------------

@command("погода")
async def weather_cmd(ctx):
    # импорт локально, только когда команда вызывается
    from pogoda.vk_send import vk_send
    from pogoda.weather import get_weather

    try:
        parts = ctx["text"].split(maxsplit=1)
        if len(parts) < 2:
            return await vk_send(ctx, "❗ Используй: !погода <город>")

        city = parts[1].strip()
        weather = await get_weather(city)

        await vk_send(ctx, f"🌦 {weather}")

    except Exception:
        await vk_send(ctx, "❌ Ошибка получения погоды")
        raise

@command("подключен")
@command("проверка")
async def check_user_cmd(ctx):
    from pogoda.vk_send import vk_send
    from db import is_user_connected

    vk = ctx["vk"]
    text = ctx["text"]
    token = ctx["token"]

    user_id = ctx["from_id"]

    # 1️⃣ если ответ на сообщение
    if ctx.get("reply"):
        user_id = ctx["reply"]["from_id"]

    # 2️⃣ если передан аргумент
    else:
        parts = text.split(maxsplit=1)
        if len(parts) > 1:
            arg = parts[1].lstrip("@")

            if arg.isdigit():
                user_id = int(arg)
            else:
                try:
                    res = vk.utils.resolveScreenName(screen_name=arg)
                    if res and res.get("type") == "user":
                        user_id = res["object_id"]
                    else:
                        return await vk_send(ctx, "❌ Пользователь не найден")
                except:
                    return await vk_send(ctx, "❌ Не удалось определить пользователя")

    # 3️⃣ проверка в БД
    connected = await is_user_connected(token, user_id)

    if connected:
        await vk_send(
            ctx,
            f"✅ Пользователь [id{user_id}|пoдключён] к боту"
        )
    else:
        await vk_send(
            ctx,
            f"❌ Пользователь [id{user_id}|не подключён] к боту"
        )

@command("ресурсы")
async def resources_cmd(ctx):
    process = psutil.Process()  # текущий процесс бота
    cpu = process.cpu_percent(interval=0.1)  # загрузка CPU процессом
    mem = process.memory_info().rss / 1024 / 1024  # в мегабайтах

    uptime = time.perf_counter() - BOT_START_TIME
    hours, rem = divmod(int(uptime), 3600)
    minutes, seconds = divmod(rem, 60)

    text = (
        f"📊 Статистика ресурсов бота:\n"
        f"• CPU: {cpu:.1f}%\n"
        f"• RAM: {mem:.1f} MB\n"
        f"• Время работы: {hours}ч {minutes}м {seconds}с"
    )
    await vk_send(ctx["vk"], ctx["peer_id"], text)

@command("uptime")
async def uptime_cmd(ctx):
    delta = time.perf_counter() - BOT_START_TIME
    hours, rem = divmod(int(delta), 3600)
    minutes, seconds = divmod(rem, 60)
    text = f"⏱ Бот работает: {hours}ч {minutes}м {seconds}с"
    await vk_send(ctx["vk"], ctx["peer_id"], text)

@command("хелп")
async def help_cmd(ctx):
    text = "📜 Список команд:\n" + "\n".join(sorted(COMMANDS.keys()))
    await vk_send(ctx["vk"], ctx["peer_id"], text)

# ------------------------ !профиль ------------------------
@command("профиль")
async def profile_cmd(ctx):
    """
    Выводит расширенную информацию о пользователе.
    Поддержка:
    - !профиль
    - в ответ на сообщение
    - !профиль <ID или screen_name>
    """
    vk = ctx["vk"]
    args = ctx["text"].split()
    user_id = ctx["from_id"]

    if ctx.get("reply"):
        user_id = ctx["reply"]["from_id"]
    elif len(args) > 1:
        arg = args[1].lstrip("@")
        if arg.isdigit():
            user_id = int(arg)
        else:
            try:
                res = vk.utils.resolveScreenName(screen_name=arg)
                if res and res.get("type") == "user":
                    user_id = res["object_id"]
                else:
                    await vk_send(vk, ctx["peer_id"], "❌ Пользователь не найден")
                    return
            except:
                await vk_send(vk, ctx["peer_id"], "❌ Не удалось преобразовать ник в ID")
                return

    try:
        users = vk.users.get(
            user_ids=user_id,
            fields=(
                "bdate,city,country,online,sex,status,domain,photo_max_orig,"
                "followers_count,home_town,occupation,university_name,interests,"
                "music,movies,games,books,about"
            )
        )
        if not users:
            await vk_send(vk, ctx["peer_id"], "❌ Пользователь не найден")
            return

        user = users[0]
        lines = []

        # Основная информация
        lines.append(f"👤 {user.get('first_name','')} {user.get('last_name','')}")
        if user.get("id"): lines.append(f"🆔 ID: {user['id']}")
        if user.get("domain"): lines.append(f"🌐 https://vk.com/{user['domain']}")
        if user.get("city"): lines.append(f"🏙 Город: {user['city']['title']}")
        if user.get("home_town"): lines.append(f"🏡 Родной город: {user['home_town']}")
        if user.get("country"): lines.append(f"🌍 Страна: {user['country']['title']}")
        if user.get("bdate"): lines.append(f"🎂 ДР: {user['bdate']}")
        if "online" in user: lines.append(f"💻 Онлайн: {'Да' if user['online'] else 'Нет'}")
        if user.get("sex"):
            sex_map = {1:"Женский",2:"Мужской"}
            lines.append(f"⚧ Пол: {sex_map.get(user['sex'],'Не указан')}")
        if user.get("status"): lines.append(f"📝 Статус: {user['status']}")
        if user.get("followers_count"): lines.append(f"👥 Подписчики: {user['followers_count']}")
        if user.get("occupation") and user["occupation"].get("name"):
            lines.append(f"💼 Работа: {user['occupation']['name']}")
        if user.get("university_name"): lines.append(f"🏫 Университет: {user['university_name']}")
        if user.get("interests"): lines.append(f"📚 Интересы: {user['interests']}")
        if user.get("music"): lines.append(f"🎵 Музыка: {user['music']}")
        if user.get("movies"): lines.append(f"🎬 Фильмы: {user['movies']}")
        if user.get("games"): lines.append(f"🎮 Игры: {user['games']}")
        if user.get("books"): lines.append(f"📖 Книги: {user['books']}")
        if user.get("about"): lines.append(f"💬 О себе: {user['about']}")

        # Фото профиля с сокращением через vk.cc
        photo_url = user.get("photo_max_orig")
        if photo_url:
            try:
                short = vk.utils.getShortLink(url=photo_url)
                short_url = short.get("short_url", photo_url)
            except:
                short_url = photo_url
            lines.append(f"📷 Фото: {short_url}")

        await vk_send(vk, ctx["peer_id"], "\n".join(lines))

    except Exception as e:
        await vk_send(vk, ctx["peer_id"], f"❌ Ошибка при получении профиля: {e}")

# ------------------------ !онлайн ------------------------
@command("онлайн")
async def online_cmd(ctx):
    peer_id = ctx["peer_id"]
    if peer_id < 2000000000:
        await vk_send(ctx["vk"], ctx["peer_id"], "❌ Команда работает только в беседах")
        return
    try:
        members = ctx["vk"].messages.getConversationMembers(peer_id=peer_id)
        profiles = members.get("profiles", [])
        items = members.get("items", [])
        admin_ids = {i["member_id"] for i in items if i.get("is_admin")}
        mod_ids = {i["member_id"] for i in items if i.get("is_owner")}
        online_users = [u for u in profiles if u.get("online") == 1]
        if not online_users:
            await vk_send(ctx["vk"], ctx["peer_id"], "😴 Сейчас никто не онлайн")
            return

        text = f"🟢 Онлайн ({len(online_users)}):\n"
        for u in online_users:
            uid = u["id"]
            name = f"{u['first_name']} {u['last_name']}"
            if uid in mod_ids:
                text += f"🛡 {name}\n"
            elif uid in admin_ids:
                text += f"⭐ {name}\n"
            else:
                text += f"{name}\n"
        await vk_send(ctx["vk"], ctx["peer_id"], text)
    except Exception as e:
        await vk_send(ctx["vk"], ctx["peer_id"], f"❌ Ошибка: {e}")

@command("юзеры")
async def users_cmd(ctx):
    tokens = ctx.get("bot_tokens", [])
    count = len(tokens)

    text = f"🟢 Бот подключен к {count} страницам\n\n"
    for i, t in enumerate(tokens, 1):
        text += f"\n"

    await vk_send(ctx["vk"], ctx["peer_id"], text)

# ------------------------ !ai ------------------------
@command("ии")
async def ai_cmd(ctx):
    parts = ctx["text"].split(maxsplit=1)
    if len(parts) < 2:
        await vk_send(ctx["vk"], ctx["peer_id"], "❗ Использование: !ai <текст>")
        return
    user_text = parts[1]
    try:
        # Пример заглушки для ИИ
        answer = f"🤖 ИИ ответ на: {user_text}"
        await vk_send(ctx["vk"], ctx["peer_id"], answer)
    except Exception as e:
        await vk_send(ctx["vk"], ctx["peer_id"], f"❌ Ошибка ИИ: {e}")

# ------------------------ !википедия ------------------------
@command("википедия")
async def wikipedia_cmd(ctx):
    parts = ctx["text"].split(maxsplit=1)
    if len(parts) < 2:
        await vk_send(ctx["vk"], ctx["peer_id"], "❗ Использование: !википедия <запрос>")
        return
    query = parts[1]
    try:
        page = wikipedia.page(query)
        summary = wikipedia.summary(query, sentences=3)
        response = f"📚 *{page.title}*\n\n{summary}\n\n"
        await vk_send(ctx["vk"], ctx["peer_id"], response)
    except wikipedia.exceptions.DisambiguationError as e:
        options = ", ".join(e.options[:5])
        await vk_send(ctx["vk"], ctx["peer_id"], f"❓ Запрос неоднозначен. Варианты: {options}")
    except wikipedia.exceptions.PageError:
        await vk_send(ctx["vk"], ctx["peer_id"], "❌ Статья не найдена")
    except Exception as e:
        await vk_send(ctx["vk"], ctx["peer_id"], f"⚠️ Ошибка: {e}")

# ------------------------ !стат ------------------------
@command("стат")
async def stats_cmd(ctx):
    count = await get_message_count(ctx["token"], ctx["from_id"])
    await vk_send(ctx["vk"], ctx["peer_id"], f"Вы отправили сообщений: {count}")

# ------------------------ !префикс ------------------------
@command("префикс")
async def prefix_cmd(ctx):
    parts = ctx["text"].split(maxsplit=2)
    if len(parts) < 2:
        prefixes = await get_prefixes(ctx["token"])
        await vk_send(ctx["vk"], ctx["peer_id"], f"Текущие префиксы: {', '.join(prefixes)}")
        return

    action = parts[1]
    if len(parts) < 3:
        await vk_send(ctx["vk"], ctx["peer_id"], "Укажи префикс для добавления/удаления")
        return

    prefix = parts[2]
    if action == "+":
        ok = await add_prefix(ctx["token"], prefix)
        await vk_send(ctx["vk"], ctx["peer_id"], f"Префикс '{prefix}' {'добавлен' if ok else 'уже существует'}")
    elif action == "-":
        ok = await remove_prefix(ctx["token"], prefix)
        await vk_send(ctx["vk"], ctx["peer_id"], f"Префикс '{prefix}' {'удален' if ok else 'не найден'}")
    else:
        await vk_send(ctx["vk"], ctx["peer_id"], "Неверное действие. Используй + или -")

# ------------------------ !ping ------------------------
@command("пинг")
async def ping_cmd(ctx):
    start = time.perf_counter()
    await vk_send(ctx["vk"], ctx["peer_id"], f"🏓 Pong! Время: {int((time.perf_counter()-start)*1000)}ms")

# ------------------------ !тайм ------------------------
@command("тайм")
async def time_cmd(ctx):
    now = datetime.datetime.now()
    await vk_send(ctx["vk"], ctx["peer_id"], f"Текущее время: {now.strftime('%Y-%m-%d %H:%M:%S')}")

@command("рестарт")
async def restart_cmd(ctx):
    if ctx["token"] not in ADMIN_TOKENS:
        await vk_send(ctx["vk"], ctx["peer_id"], "❌ Команда доступна только администратору!")
        return

    await vk_send(ctx["vk"], ctx["peer_id"], "♻️ Бот перезагружается...")

    python = sys.executable
    os.execv(python, [python] + sys.argv)



