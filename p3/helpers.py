from django.conf import settings
from django.core.files import storage


def get_secure_storage():
    return storage.FileSystemStorage(
        location=settings.SECURE_MEDIA_ROOT,
        base_url=settings.SECURE_MEDIA_URL,
    )
