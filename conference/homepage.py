from django.conf import settings
from django.http import JsonResponse
from django.template.response import TemplateResponse
from django.utils.lorem_ipsum import words, paragraphs


from .models import Sponsor


CCD_GOOGLEMAPS_URL = "https://goo.gl/maps/X57SxAPbiJV3Fcig9"
CCD_OSM_URL = (
    "https://www.openstreetmap.org/way/60270053"
)


def homepage(request):
    # Static homepage, used in ep2019. In ep2020, homepage is served by the CMS
    sponsors = Sponsor.objects.filter(
        sponsorincome__conference=settings.CONFERENCE_CONFERENCE
    )

    return TemplateResponse(
        request,
        "conference/homepage/home.html",
        {
            "sponsors": sponsors,
            "CCD_GOOGLEMAPS_URL": CCD_GOOGLEMAPS_URL,
            "CCD_OSM_URL": CCD_OSM_URL,
        },
    )


def homepage_sponsors(request):
    # Sponsor data to be rendered on the homepage
    sponsors = Sponsor.objects.filter(
        sponsorincome__conference=settings.CONFERENCE_CONFERENCE
    ).values('sponsor', 'url', 'logo', 'alt_text', 'title_text')

    return JsonResponse({'sponsors': list(sponsors)})


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
