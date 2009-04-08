from django.conf import settings

def highlight(request):
    """
    Aggiunge il messaggio da mostrare in tutte le pagine
    """
    return {
        'HIGHLIGHT': '<a href="/pycon3/registrazione/">Mancano solo <strong>10 giorni</strong> alla fine dell\'early bird</a>',
    }
