
import django.conf


def settings(request):
    names = (
        'NEWSLETTER_SUBSCRIBE_URL',
        'TWITTER_USER',
        'GOOGLE_ANALYTICS',
    )
    output = {}
    for x in names:
        output[x] = getattr(django.conf.settings, 'P3_' + x, None)
    return output
