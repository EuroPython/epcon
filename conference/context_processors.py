import settings

from django.conf import settings as dsettings

def stuff(request):
    """
    Aggiunge le variabili relative alla STUFF directory
    """
    stuff = settings.STUFF_URL
    ctx = {
        'STUFF_URL': stuff,
        'SPONSOR_LOGO_URL': '%ssponsor/' % stuff,
        'MEDIAPARTNER_LOGO_URL': '%smedia-partner/' % stuff,
        'QUOTE_FACE_URL': '%squote/' % stuff,
        'SPEAKER_FACE_URL': '%sspeaker/' % stuff,
        'SLIDE_FILE_URL': '%sslides/' % stuff,
        'DEFAULT_URL_PREFIX': getattr(dsettings, 'DEFAULT_URL_PREFIX', ''),
        'CONFERENCE': settings.CONFERENCE,
    }
    if settings.GOOGLE_MAPS:
        ctx['GOOGLE_MAPS_KEY'] = settings.GOOGLE_MAPS['key']
    return ctx

def current_url(request):
    return {
        'CURRENT_URL': dsettings.DEFAULT_URL_PREFIX + request.path,
    }
