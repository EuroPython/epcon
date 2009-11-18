import settings

def stuff(request):
    """
    Aggiunge le variabili relative alla STUFF directory
    """
    stuff = settings.CONFERENCE_STUFF_URL
    ctx = {
        'STUFF_URL': stuff,
        'SPONSOR_LOGO_URL': '%ssponsor/' % stuff,
        'MEDIAPARTNER_LOGO_URL': '%smedia-partner/' % stuff,
        'SPEAKER_FACE_URL': '%sspeaker/' % stuff,
        'SLIDE_FILE_URL': '%sslides/' % stuff,
    }
    if settings.CONFERENCE_GOOGLE_MAPS:
        ctx['GOOGLE_MAPS_KEY'] = settings.CONFERENCE_GOOGLE_MAPS['key']
    return ctx
