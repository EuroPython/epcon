from django.conf import settings

def stuff(request):
    """
    Add the variables realted to the STUFF directory
    """
    stuff = settings.MEDIA_URL
    ctx = {
        'STUFF_URL': stuff,
        'SPONSOR_LOGO_URL': '%ssponsor/' % stuff,
        'MEDIAPARTNER_LOGO_URL': '%smedia-partner/' % stuff,
        'QUOTE_FACE_URL': '%squote/' % stuff,
        'SPEAKER_FACE_URL': '%sspeaker/' % stuff,
        'SLIDE_FILE_URL': '%sslides/' % stuff,
        'DEFAULT_URL_PREFIX': getattr(settings, 'DEFAULT_URL_PREFIX', ''),
        'CONFERENCE': settings.CONFERENCE_CONFERENCE,
    }
    return ctx

def current_url(request):
    return {
        'CURRENT_URL': settings.DEFAULT_URL_PREFIX + request.path,
    }
