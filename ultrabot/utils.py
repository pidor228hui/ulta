import random

async def vk_send(vk, peer_id, message):
    """
    Безопасная отправка сообщений через vk_api.
    vk — объект vk_api.get_api()
    peer_id — ID чата или пользователя
    message — текст сообщения
    """
    try:
        vk.messages.send(
            peer_id=peer_id,
            message=message,
            random_id=random.randint(1, 2**31 - 1)  # нужен random_id для VK
        )
    except Exception as e:
        print(f"[vk_send error] {e}")