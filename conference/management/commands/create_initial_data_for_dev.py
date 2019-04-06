import csv
import random
from datetime import timedelta
from io import StringIO

from cms.api import add_plugin, create_page, publish_page
from django.conf import settings
from django.core.exceptions import FieldError
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import lorem_ipsum, timezone
from djangocms_text_ckeditor.cms_plugins import TextPlugin

from assopy.models import AssopyUser, Country, Vat
from conference.fares import pre_create_typical_fares_for_conference
from conference.models import (
    Conference,
    ConferenceTag,
    News,
    TALK_STATUS,
    Speaker,
)
from conference.tests.factories.fare import SponsorIncomeFactory
from conference.tests.factories.talk import TalkFactory
from conference.cfp import add_speaker_to_talk
from conference.accounts import get_or_create_attendee_profile_for_new_user


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
            # For easier testing open CFP
            cfp_start=timezone.now() - timedelta(days=3),
            cfp_end=timezone.now() + timedelta(days=3),
        )

        print("Creating an admin user")
        admin = AssopyUser.objects.create_superuser(
            username="admin", email="admin@admin.com", password="europython"
        )

        print("Creating regular users")
        alice = AssopyUser.objects.create_user(
            email="alice@europython.eu",
            password="europython",
            active=True,
        )
        bob = AssopyUser.objects.create_user(
            email="bob@europython.eu",
            password="europython",
            active=True,
        )
        cesar = AssopyUser.objects.create_user(
            email="cesar@europython.eu",
            password="europython",
            active=True,
        )

        print("Making some talk proposals")
        for user in alice, bob, cesar:
            speaker, _ = Speaker.objects.get_or_create(user=user.user)
            talk = TalkFactory(status=TALK_STATUS.proposed)
            talk.setAbstract("some abstract")
            talk.created_by = user.user
            talk.save()
            add_speaker_to_talk(speaker, talk)
            get_or_create_attendee_profile_for_new_user(user.user)

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

        create_tags()


def create_tags():
    """
    Uses dump for pre-2019 data to populate ConferenceTag instances for CFP
    """

    INPUT = """
    "Python general",Python
    R,"Other Programming Languages"
    Java,"Other Programming Languages"
    C-Languages,"Other Programming Languages"
    Analytics,"Data Science"
    Visualization,"Data Science"
    "Big Data","Data Science"
    Predictions,"Data Science"
    MongoDB,Databases
    "Web Servers and MicroFWs (Flask/Tornado/Nginx/...)",Web
    Ipython,Python
    "Web General",Web
    Socket,DevOps
    Django,"Application Frameworks"
    Docker,DevOps
    Security,Security
    Privacy,Security
    Odoo,"Application Frameworks"
    "Scientific Libraries (Numpy/Pandas/SciKit/...)","Data Science"
    Pyramid,"Application Frameworks"
    Plone,"Application Frameworks"
    "Data Science","Data Science"
    Machine-Learning,"Data Science"
    PostgreSQL,Databases
    Django-Girls,Community
    Agile,"Development Methods"
    Documentation,Programming
    "DevOps general",DevOps
    Community,Community
    "Natural Language Processing","Data Science"
    PyPy,Python
    Open-Source,"Open Source"
    Linux,"Operating Systems"
    "SQL Alchemy",Databases
    Communication,Community
    Tooling,Programming
    "Test Libraries (pyTest/node/...)",Testing
    MySQL,Databases
    Packaging,Python
    "JavaScript Web Frameworks (AngularJS/ReactJS/...)",Web
    "Internet of Things (IoT)",Hardware
    Performance,Programming
    Saltstack,DevOps
    Management,"Development Methods"
    Scrum,"Development Methods"
    Kanban,"Development Methods"
    Internationalization,Programming
    "Behavior Driven Development (BDD)","Development Methods"
    HTML5,Web
    NoSQL,Databases
    OpenGL,Web
    "Test Driven Development (TDD)",Testing
    Education,Educational
    CPython,Python
    APIs,Web
    "Python 3",Python
    "Best Practice","Best Practice and Use Cases"
    Development,Programming
    Testing,Testing
    Beginners,Educational
    Programming,Programming
    Cython,Python
    "Deep Learning","Data Science"
    Unix,"Operating Systems"
    "Case Study","Case Study"
    E-Commerce,Web
    "Distributed Systems",DevOps
    "Functional Programming",Programming
    Architecture,Programming
    OpenStack,DevOps
    "Raspberry PI",Hardware
    Teaching,"Everything Else"
    "Meta Classes",Programming
    "Public Cloud (AWS/Google/...)",DevOps
    "Augmented Reality","Everything Else"
    Engineering,"Everything Else"
    Physics,Sciences
    "Clean Code",Educational
    "System Administration",DevOps
    Mix-Ins,Programming
    "Static Analysis","Everything Else"
    "Compiler and Interpreters",Python
    Type-Hinting,Programming
    "Web Crawling",Web
    JavaScript,"Other Programming Languages"
    NodeJS,Web
    "Conferences and Meet-Ups",Community
    Databases,Databases
    Infrastructure,DevOps
    "Elastic Search",Databases
    Go-Lang,"Other Programming Languages"
    HTTP,Web
    Operations,DevOps
    "Configuration Management (Ansible/Fabric/Chef/...)",DevOps
    "Deployment/Continuous Integration and Delivery",DevOps
    Jenkins,Testing
    Science,Sciences
    Authentication,Security
    3D,"Everything Else"
    Blender,"Everything Else"
    Diversity,Community
    Robotics,Hardware
    Human-Machine-Interaction,Hardware
    Debugging,Testing
    "Euro Python and EPS",Community
    LaTeX,"Other Programming Languages"
    Game-Development,"Everything Else"
    Kivy,Python
    Cross-Platform-Development,Python
    Git,DevOps
    PyQt,Programming
    Virtualization,DevOps
    "Software Design",Programming
    Multi-Processing,Programming
    Multi-Threading,Programming
    Windows,"Operating Systems"
    "Messaging and Job Queues (RabbitMQ/Redis/...)",DevOps
    "Fun and Humor","Everything Else"
    Command-Line,Programming
    CMS,Web
    "GEO and GIS","Everything Else"
    "Graph Databases",Databases
    Abstractions,"Everything Else"
    "Code Analysis",Programming
    Wearables,Hardware
    Mobile,Web
    "Jupyter/iPython Notebook",Python
    RESTful,Web
    Cryptography,Security
    OpenCV,Hardware
    "ASYNC / Concurreny",Programming
    "Virtual Env",Programming
    PyPi,Python
    Micro-Computers,Hardware
    Microservices,Programming
    Scaling,DevOps
    "Python Software Foundation (PSF)",Community
    workforce,Business
    DIY,"Everything Else"
    "Image Processing","Everything Else"
    "Mac OS X","Operating Systems"
    "Data Structures",Programming
    "System Architecture",DevOps
    Algorithms,"Data Science"
    PyLadies,Community
    "The Answer to Life the Universe and Everything Else","Everything Else"
    Gadgets,Hardware
    "All Other Programming Languages","Other Programming Languages"
    "Use Case","Best Practice and Use Cases"
    Sensors,Hardware
    "Other Hardware",Hardware
    failures/mistakes,"Best Practice and Use Cases"
    clients,Business
    freelancing,Business
    "Mind Bending","Everything Else"
    Templating,Web
    legacy-code,Programming
    MicroPython,Python
    "Python 2",Python
    python,Python
    Data,"Data Science"
    Structures,"Data Science"
    Web,Web
    Business,Business
    Notebook,"Data Science"
    Jupyter/iPython,"Data Science"
    Life,Community
    Universe,Sciences
    Deep,"Data Science"
    Learning,"Data Science"
    Internet,Web
    "Internet of Things",DevOps
    EPS,Community
    EuroPython,Community
    "Open Stack",DevOps
    finance,""
    Trading,""
    """.strip()

    buffer = StringIO(INPUT)

    reader = csv.reader(buffer)
    for line in reader:
        ConferenceTag.objects.create(
            name=line[0].strip(), category=line[1].strip()
        )
        print("Created tag", line[0].strip())
