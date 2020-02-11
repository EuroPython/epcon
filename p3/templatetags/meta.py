from django import template
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def render_meta(context, title=""):
    request = context.get("request")
    page = context.get("current_page")
    cms_page_title = page.get_title() if page else ""

    title = title or context.get("title", "") or cms_page_title
    title = f"{title} &amp; " if title else ""

    description = ""
    page_title = (
        f"{title}EuroPython 2020 &middot; Dublin, Ireland, 20-26 July 2020"
    )
    page_url = context["CURRENT_URL"]

    image_url = context.get("social_image_url") or request.build_absolute_uri(
        static("img/ep2020-social-dark.png")
    )

    TEMPLATE = f"""
    <title>{page_title}</title>
    <meta name="title" content="{page_title}">
    <meta name="description" content="{description}">
    <meta name="author" content="EuroPython">

    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="website">
    <meta property="og:url" content="{page_url}">
    <meta property="og:title" content="{page_title}">
    <meta property="og:description" content="{description}">
    <meta property="og:image" content="{image_url}">

    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:url" content="{page_url}">
    <meta property="twitter:title" content="{page_title}">
    <meta property="twitter:description" content="{description}">
    <meta property="twitter:image" content="{image_url}">
    """

    return mark_safe(TEMPLATE)
