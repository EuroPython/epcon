from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.core.exceptions import FieldError

from cms.api import create_page, add_plugin, publish_page
from djangocms_text_ckeditor.cms_plugins import TextPlugin

from assopy.models import AssopyUser, Vat, Country
from conference.fares import pre_create_typical_fares_for_conference
from conference.models import Conference
from conference.tests.factories.fare import SponsorIncomeFactory
from tests.common_tools import create_homepage_in_cms


DEFAULT_VAT_RATE = "0.2"  # 20%


class Command(BaseCommand):
    """
    Creates bunch of data that's required for new developer setup.
    Mostly django CMS pages.
    """

    @transaction.atomic
    def handle(self, *args, **options):
        conference, _ = Conference.objects.get_or_create(
            code=settings.CONFERENCE_CONFERENCE,
            name=settings.CONFERENCE_CONFERENCE,
        )

        print("Creating an admin user")
        admin = AssopyUser.objects.create_superuser(
            username="admin", email="admin@admin.com", password="europython"
        )

        print("Creating regular users")
        AssopyUser.objects.create_user(
            email="alice@europython.eu",
            password="europython",
            active=True,
            send_mail=False,
        )
        AssopyUser.objects.create_user(
            email="bob@europython.eu",
            password="europython",
            active=True,
            send_mail=False,
        )
        AssopyUser.objects.create_user(
            email="cesar@europython.eu",
            password="europython",
            active=True,
            send_mail=False,
        )

        # Create homepage with some sample data.
        homepage = create_homepage_in_cms()

        print(
            "Created page: ",
            homepage.reverse_id,
            homepage.title_set.first().title,
            homepage.template,
        )

        def new_page(rev_id, title, **kwargs):
            try:
                page = create_page(
                    reverse_id=rev_id,
                    title=title,
                    language="en",
                    template=(
                        "ep19/bs/content/"
                        "generic_content_page_with_sidebar.html"
                    ),
                    published=True,
                    publication_date=timezone.now(),
                    in_navigation=True,
                    **kwargs,
                )
                add_plugin(
                    placeholder=page.placeholders.get(slot="page_content"),
                    plugin_type=TextPlugin,
                    language="en",
                    body=f"This is the page content for {title}",
                )
                publish_page(page, user=admin.user, language="en")
                print("Created page: ", page.reverse_id, title, page.template)
                return page

            # FieldError happens to be what django cms is using when we want to
            # create another page with the same reverse_id
            except FieldError as e:
                print("Warning: ", e)

        program_page = new_page("program", "Program")

        for rev_id, title in [
            ("speakers", "Speakers"),
            ("tranings", "Tranings"),
            ("workshops", "Workshops"),
            ("talks_and_conference_days", "Talks and Conference Days"),
            ("social-event", "Social Event"),
            ("sprints", "Sprint"),
            ("tickets", "Tickets"),
        ]:
            new_page(rev_id, title, parent=program_page)

        location_page = new_page("location", "Location")
        for rev_id, title in [
            ("explore-basel", "Explore City of Basel"),
            ("visa", "Visa"),
            ("conference-venue", "Conference Venue"),
            ("sprints-venue", "Workshops & Sprints Venue"),
        ]:
            new_page(rev_id, title, parent=location_page)

        about_europython_page = new_page("about", "About EuroPython")
        for rev_id, title in [
            ("volunteers", "Volunteers"),
            ("workgroups", "Workgroups"),
            ("photos", "Photos"),
            ("videos", "Videos"),
            ("social-media", "Social Media"),
            ("eps", "EuroPythoon Society"),
            ("previous-editions", "Previous Editions"),
            ("help-organize", "Help Organize next EuroPython"),
        ]:
            new_page(rev_id, title, parent=about_europython_page)

        sponsor_page = new_page("sponsor", "Sponsors")
        for rev_id, title in [
            ("become-a-sponsor", "How to become a Sponsor"),
            ("sponsor-packages", "Sponsorship packages"),
            ("additional-information", "Additional Information"),
        ]:
            new_page(rev_id, title, parent=sponsor_page)

        faq_page = new_page("faq", "FAQ")
        for rev_id, title in [
            ("tips-for-attendees", "Tips for Attendees"),
            ("tips-for-speakers", "Tips for Speakers"),
            ("tips-for-speakers", "Tips for Speakers"),
        ]:
            new_page(rev_id, title, parent=faq_page)

        new_page("code-of-conduct", "Code of Conduct")

        print("Creating some countries")
        for iso, name in [
            ("PL", "Poland"),
            ("DE", "Germany"),
            ("FR", "France"),
            ("SE", "Sweden"),
            ("IT", "Italy"),
            ("CH", "Switzerland"),
        ]:
            Country.objects.get_or_create(iso=iso, name=name)

        print("Creating sponsors")
        SponsorIncomeFactory(
            conference=conference,
            sponsor__sponsor="EuroPython Society",
            sponsor__url="https://www.europython-society.org",
            sponsor__logo__color="yellow",
        )

        for color in "blue", "orange", "teal", "purple", "red":
            SponsorIncomeFactory(
                conference=conference, sponsor__logo__color=color
            )

        print("Pre creating fares")
        default_vat_rate, _ = Vat.objects.get_or_create(value=DEFAULT_VAT_RATE)
        pre_create_typical_fares_for_conference(
            settings.CONFERENCE_CONFERENCE, default_vat_rate, print_output=True
        )
