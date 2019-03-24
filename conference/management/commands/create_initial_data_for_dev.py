from datetime import timedelta
import random

from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction
from django.utils import timezone, lorem_ipsum
from django.core.exceptions import FieldError

from cms.api import create_page, add_plugin, publish_page
from djangocms_text_ckeditor.cms_plugins import TextPlugin

from assopy.models import AssopyUser, Vat, Country
from conference.fares import pre_create_typical_fares_for_conference
from conference.models import Conference, News
from conference.tests.factories.fare import SponsorIncomeFactory


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
        )
        AssopyUser.objects.create_user(
            email="bob@europython.eu",
            password="europython",
            active=True,
        )
        AssopyUser.objects.create_user(
            email="cesar@europython.eu",
            password="europython",
            active=True,
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
                    placeholder=page.placeholders.get(slot="text"),
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

        program_page = new_page("faq", "FAQ")
        for rev_id, title in [
            ("tickets", "Buy Tickets"),
            ("submit-proposal", "Submit Proposal"),
            ("tips-for-attendees", "Tips for Attendees"),
            ("volunteers", "Volunteers"),
            ("sign-up-as-session-chair", "Sign up as Session Chair"),
            ("financial-aid", "Financial Aid"),
            ("visa", "Visa"),
        ]:
            new_page(rev_id, title, parent=program_page)

        program_page = new_page("program", "Program")
        for rev_id, title in [
            ("workshops", "Workshops"),
            ("trainings", "Trainings"),
            ("schedule", "Schedule"),
            ("talks", "Talks"),
            ("speakers", "Speakers"),
            ("tips-for-speakers", "Tips for Speakers"),
            ("speaker-release-agreement", "Speaker Release Agreement"),
            ("open-spaces", "Open Spaces"),
            ("social-event", "Social Event"),
            ("sprints", "Sprints"),
        ]:
            new_page(rev_id, title, parent=program_page)

        location_page = new_page("location", "Location")
        for rev_id, title in [
            ("conference-venue", "Conference Venue"),
            ("workshops-and-sprints-venue", "Workshops & Sprints Venue"),
            ("basel", "Basel"),
            ("travel", "Travel"),
            ("accommodation", "Accommodation"),
            ("where-to-eat", "Where to Eat and Drink"),
        ]:
            new_page(rev_id, title, parent=location_page)

        sponsor_page = new_page("sponsor", "Sponsor")
        for rev_id, title in [
            ("become-a-sponsor", "Become a Sponsor"),
            ("sponsor-packages", "Packages"),
            ("sponsor-options", "Additional Options"),
            ("sponsor-information", "Additional Information"),
            ("sponsor-jobboard", "Job Board"),
        ]:
            new_page(rev_id, title, parent=sponsor_page)

        about_europython_page = new_page("about", "About")
        for rev_id, title in [
            ("social-media", "Social Media"),
            ("code-of-conduct", "Code of Conduct"),
            ("privacy", "Privacy policy"),
            ("workgroups", "2019 Team"),
            ("photos", "Photos"),
            ("videos", "Videos"),
            ("eps", "EuroPython Society"),
            ("previous-editions", "Previous Editions"),
            ("help-organize", "Help Organize next EuroPython"),
            ("faq", "FAQ"),
        ]:
            new_page(rev_id, title, parent=about_europython_page)

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

        # News

        print("Creating news...")
        for _ in range(20):
            News.objects.create(
                conference=conference,
                title=lorem_ipsum.sentence(),
                content=lorem_ipsum.paragraph(),
                status=News.STATUS.PUBLISHED,
                published_date=(
                    timezone.now() - timedelta(days=random.randint(10, 20))
                ),
            )

        News.objects.create(
            conference=conference,
            title="Launch of new website",
            content=lorem_ipsum.paragraph(),
            status=News.STATUS.PUBLISHED,
            published_date=timezone.now() - timedelta(days=3),
        )

        News.objects.create(
            conference=conference,
            title="Call For Proposal is now Open",
            content=lorem_ipsum.paragraph(),
            status=News.STATUS.PUBLISHED,
            published_date=timezone.now() - timedelta(hours=5),
        )

        News.objects.create(
            conference=conference,
            title="Rescheduled a talk",
            content="We had to reschedule talk #1237 to slot #ABC on Friday",
            status=News.STATUS.PUBLISHED,
            published_date=timezone.now(),
        )

        News.objects.create(
            conference=conference,
            title="This is just a draft",
            content="With draft content",
            status=News.STATUS.DRAFT,
            published_date=None,
        )
