from django.conf import settings

def stuff(request):
    """
    Aggiunge le variabili relative alla STUFF directory
    """
    stuff = '%sstuff/' % settings.MEDIA_URL
    return {
        'STUFF_URL': stuff,
        'SPONSOR_LOGO_URL': '%ssponsor/' % stuff,
        'SPEAKER_FACE_URL': '%sspeaker/' % stuff,
        'SLIDE_FILE_URL': '%sslides/' % stuff,
    }
