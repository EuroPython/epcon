from django.conf import settings


def epcon_ctx(request):
    return {
        'CURRENT_URL': settings.DEFAULT_URL_PREFIX + request.path,
        'DEFAULT_URL_PREFIX': settings.DEFAULT_URL_PREFIX,
        'CONFERENCE': settings.CONFERENCE_CONFERENCE,
    }
