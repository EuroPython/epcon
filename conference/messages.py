from django.contrib.messages.storage.cookie import CookieStorage
from django.contrib.messages.storage.session import SessionStorage
from django.contrib.messages.storage.fallback import FallbackStorage


class CustomCookieStorage(CookieStorage):
    """
    Storing messages in a different cookie to drop all preceeding messages.
    TODO umgelurgel: remove this after ep2019 and before ep2020
    """
    cookie_name = "ep-messages"


class CustomFallbackStorage(FallbackStorage):
    storage_classes = (CustomCookieStorage, SessionStorage)
