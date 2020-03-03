from django.template.response import TemplateResponse
from django.utils.lorem_ipsum import words, paragraphs
from django.conf import settings

from .models import News, Sponsor


CCD_GOOGLEMAPS_URL = "https://goo.gl/maps/X57SxAPbiJV3Fcig9"
CCD_OSM_URL = (
    "https://www.openstreetmap.org/way/60270053"
)


def homepage(request):
    latest_3_news = News.objects.filter(
        status=News.STATUS.PUBLISHED,
        conference__code=settings.CONFERENCE_CONFERENCE,
    )[:3]
    sponsors = Sponsor.objects.filter(
        sponsorincome__conference=settings.CONFERENCE_CONFERENCE
    )

    return TemplateResponse(
        request,
        "conference/homepage/home.html",
        {
            "latest_3_news": latest_3_news,
            "sponsors": sponsors,
            "CCD_GOOGLEMAPS_URL": CCD_GOOGLEMAPS_URL,
            "CCD_OSM_URL": CCD_OSM_URL,
        },
    )


def generic_content_page(request):
    return TemplateResponse(
        request, 'conference/content/generic_content_page.html', {
            'lorem_words': words,
            'lorem_paragraphs': paragraphs,
        }
    )


def generic_content_page_with_sidebar(request):
    return TemplateResponse(
        request, 'conference/content/generic_content_page_with_sidebar.html', {
            'lorem_words': words,
            'lorem_paragraphs': paragraphs,
        }
    )
