import aiohttp

async def get_weather(city: str) -> str:
    url = f"https://wttr.in/{city}?format=3"

    timeout = aiohttp.ClientTimeout(total=5)

    async with aiohttp.ClientSession(timeout=timeout) as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return "❌ Не удалось получить погоду"

            text = await resp.text()
            return text.strip()
