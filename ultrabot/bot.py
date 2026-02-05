import asyncio
from worker import bot_worker

# Читаем токены из файла
with open("config/tokens.txt", "r", encoding="utf-8") as f:
    all_tokens = [line.strip() for line in f if line.strip()]

async def main():
    tasks = [asyncio.create_task(bot_worker(t, all_tokens)) for t in all_tokens]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())