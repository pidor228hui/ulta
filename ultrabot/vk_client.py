import vk_api


def get_vk(token: str):
    session = vk_api.VkApi(token=token)
    return session.get_api()
