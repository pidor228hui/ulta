async def vk_send(ctx, message: str):
    """
    Отправка сообщения через VK.
    ctx: dict с vk и peer_id
    message: текст сообщения
    """
    vk = ctx["vk"]
    peer_id = ctx["peer_id"]

    vk.messages.send(
        peer_id=peer_id,
        message=message,
        random_id=0
    )
