from django.template.response import TemplateResponse
from django.utils.lorem_ipsum import words, paragraphs


def homepage(request):
    return TemplateResponse(
        request, 'ep19/bs/homepage/home.html', {}
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
