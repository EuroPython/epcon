from django.template.response import TemplateResponse
from django.utils.lorem_ipsum import words, paragraphs
from django import forms
from .models import News


FHNW_OSM_URL = (
    "https://www.openstreetmap.org/way/608859213#map=19/47.53473/7.64166"
)
FHNW_GOOGLEMAPS_URL = "https://goo.gl/maps/F6tYGeZKrzn"

BCC_GOOGLEMAPS_URL = "https://goo.gl/maps/ysbv2mjqQQS2"
BCC_OSM_URL = (
    "https://www.openstreetmap.org/node/3092896596#map=18/47.56256/7.59903"
)

def homepage(request):
    latest_3_news = News.objects.filter(status=News.STATUS.PUBLISHED)[:3]

    return TemplateResponse(
        request, 'ep19/bs/homepage/home.html', {
            'latest_3_news': latest_3_news,
            'FHNW_OSM_URL': FHNW_OSM_URL,
            'FHNW_GOOGLEMAPS_URL': FHNW_GOOGLEMAPS_URL,
            'BCC_GOOGLEMAPS_URL': BCC_GOOGLEMAPS_URL,
            'BCC_OSM_URL': BCC_OSM_URL,
        }
    )


def generic_content_page(request):
    return TemplateResponse(
        request, 'ep19/bs/content/generic_content_page.html', {
            'lorem_words': words,
            'lorem_paragraphs': paragraphs,
        }
    )


def generic_content_page_with_sidebar(request):
    return TemplateResponse(
        request, 'ep19/bs/content/generic_content_page_with_sidebar.html', {
            'lorem_words': words,
            'lorem_paragraphs': paragraphs,
        }
    )


def form_testing(request):

    class AForm(forms.Form):
        name = forms.CharField()
        password = forms.CharField(widget=forms.widgets.PasswordInput)
        email = forms.EmailField()
        textarea = forms.CharField(widget=forms.widgets.Textarea)

    return TemplateResponse(
        request, 'ep19/bs/form_testing.html', {
            'form': AForm()
        }
    )
