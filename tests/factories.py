import datetime
import functools
import random
import uuid
from datetime import timedelta
from random import randint

import factory
import factory.django
import factory.fuzzy
from django_factory_boy import auth as auth_factories
from faker import Faker

from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils import timezone

from assopy.models import Vat, VatFare
from conference.models import (
    AttendeeProfile,
    Conference,
    Fare,
    Talk,
    Ticket,
    TALK_LANGUAGES,
    TICKET_TYPE,
    TALK_LEVEL,
    TALK_STATUS,
    random_shortuuid,
)
from conference.fares import ALL_POSSIBLE_FARE_CODES
from p3.models import TICKET_CONFERENCE_SHIRT_SIZES, TICKET_CONFERENCE_DIETS


fake = Faker()
Iterator = functools.partial(factory.Iterator, getter=lambda x: x[0])


DEFAULT_VAT_RATE = "20"  # 20%


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "auth.User"

    username = factory.fuzzy.FuzzyText()
    password = factory.PostGenerationMethodCall("set_password", "123456")
    is_active = True
    email = factory.fuzzy.FuzzyText(suffix="@bar.it")
    assopy_user = factory.RelatedFactory("tests.factories.AssopyUserFactory", "user")


class AssopyUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.AssopyUser"

    user = factory.SubFactory(
        UserFactory, assopy_user=factory.LazyAttribute(lambda assopy_user: assopy_user)
    )


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Country"

    iso = factory.Faker("country_code")
    name = factory.Faker("country")


class VatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Vat"

    value = 20


class FareFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Fare"

    price = 10

    @factory.lazy_attribute
    def conference(self):
        # If a conference instance exists, use its code; otherwise, use a hardcoded value
        conference = Conference.objects.first()
        if conference:
            return conference.code
        else:
            return "testconf"

    @factory.lazy_attribute
    def code(self):
        return random.choice(list(ALL_POSSIBLE_FARE_CODES.keys()))

    @factory.lazy_attribute
    def name(self):
        return "EuroPython2019 – %s" % ALL_POSSIBLE_FARE_CODES[self.code]

    @factory.lazy_attribute
    def start_validity(self):
        return timezone.now() - timezone.timedelta(days=10)

    @factory.lazy_attribute
    def end_validity(self):
        return timezone.now() + timezone.timedelta(days=10)

    @factory.post_generation
    def vat_set(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for vat in extracted:
                VatFare.objects.get_or_create(fare=self, vat=vat)
        else:
            default_vat_rate, _ = Vat.objects.get_or_create(value=DEFAULT_VAT_RATE)
            VatFare.objects.get_or_create(fare=self, vat=default_vat_rate)


class VatFareFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.VatFare"

    vat = factory.SubFactory(VatFactory)
    fare = factory.SubFactory(
        FareFactory, vats=factory.LazyAttribute(lambda vat_fare: vat_fare)
    )


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Ticket"

    user = factory.SubFactory(UserFactory)
    fare = factory.SubFactory(FareFactory)


class OrderItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.OrderItem"

    ticket = factory.SubFactory(TicketFactory)
    vat = factory.SubFactory(VatFactory)
    # NOTE umgelurgel (2018-10-20)
    # As this depends on `OrderFactory` to work independently, this factory is not independent either.
    order = factory.SubFactory("tests.factories.OrderFactory")


class OrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Order"

    user = factory.SubFactory(AssopyUserFactory)
    payment = "cc"
    _complete = False
    # NOTE umgelurgel (2018-10-20)
    # `items` needs to be passed to the Order.objects.create(), which is a list of (FareFactory, dict)
    # The spaghetti of signal dependencies makes it challenging to identify where or why
    # does that fail to work correctly.
    # This also requires to mock out email sending in tests that use it.
    # items = factory.LazyAttribute(lambda order: [(FareFactory(), {"qty": 1})])

    country = factory.SubFactory(CountryFactory)

    @factory.lazy_attribute
    def address(self):
        return "\n".join([fake.address(), self.country.name])


class AssopyUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.AssopyUser"

    user = factory.SubFactory(auth_factories.UserFactory)


class CreditCardOrderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Order"

    user = factory.SubFactory(AssopyUserFactory)

    payment = "cc"  # cc because stripe is a credit card
    items = []


class CouponFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Coupon"

    conference = factory.Iterator(Conference.objects.all())
    value = "10%"
    code = factory.LazyAttribute(lambda _: uuid.uuid4().hex)
    start_validity = factory.LazyAttribute(lambda _: timezone.now().date())
    end_validity = factory.LazyAttribute(
        lambda _: timezone.now().date() + timedelta(days=1)
    )

    @factory.post_generation
    def fares(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for fare in extracted:
                self.fares.add(fare)
        else:
            self.fares.add(*Fare.objects.all())


class AttendeeProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.AttendeeProfile"

    user = factory.SubFactory(auth_factories.UserFactory)
    slug = factory.LazyAttribute(
        lambda a: slugify("%s %s" % (a.user.first_name, a.user.last_name))
    )

    @factory.lazy_attribute
    def uuid(self):
        return AttendeeProfile.objects.randomUUID(6)

    birthday = factory.fuzzy.FuzzyDate(start_date=datetime.date(1950, 1, 1))


class ConferenceTagFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.ConferenceTag"

    category = factory.Faker("word")
    name = factory.Faker("word")


class ConferenceTaggedItemFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.ConferenceTaggedItem"

    tag = factory.SubFactory(ConferenceTagFactory)


class ConferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Conference"

    code = settings.CONFERENCE_CONFERENCE
    name = factory.Faker("sentence", nb_words=6, variable_nb_words=True)

    cfp_start = factory.LazyAttribute(
        lambda conf: conf.conference_start - datetime.timedelta(days=50)
    )
    cfp_end = factory.LazyAttribute(
        lambda conf: conf.cfp_start + datetime.timedelta(days=+20)
    )

    @factory.lazy_attribute
    def conference_start(self):
        return fake.date_time_this_decade(before_now=True, after_now=True).date()

    # conference_start = factory.Faker('date_time_this_decade', before_now=True, after_now=True)
    conference_end = factory.LazyAttribute(
        lambda conf: (conf.conference_start + datetime.timedelta(days=+5))
    )

    voting_start = factory.LazyAttribute(
        lambda conf: conf.cfp_end + datetime.timedelta(days=10)
    )
    voting_end = factory.LazyAttribute(
        lambda conf: conf.voting_start + datetime.timedelta(days=5)
    )


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Ticket"

    user = factory.SubFactory(auth_factories.UserFactory)
    name = factory.Faker("sentence", nb_words=4, variable_nb_words=True)
    fare = factory.SubFactory(FareFactory)
    frozen = factory.Faker("random_element", elements=(True, False))
    ticket_type = Iterator(TICKET_TYPE)


class SponsorFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Sponsor"

    sponsor = factory.Faker("company")
    slug = factory.LazyAttribute(lambda sponsor: slugify(sponsor.sponsor))
    url = factory.Faker("url")
    # By default the ImageField will create a mono-colour square.
    logo = factory.django.ImageField(width=190, height=90, color="green", format="PNG")


class SponsorIncomeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.SponsorIncome"

    sponsor = factory.SubFactory(SponsorFactory)
    conference = factory.SubFactory(ConferenceFactory)
    income = factory.LazyAttribute(lambda f: randint(1000, 10000))


class TalkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Talk

    title = factory.LazyAttribute(
        lambda talk: factory.Faker(
            "sentence", nb_words=6, variable_nb_words=True
        ).generate({})[:80]
    )
    sub_title = factory.Faker("sentence", nb_words=12, variable_nb_words=True)

    duration = 30

    uuid = factory.LazyAttribute(lambda t: random_shortuuid())
    slug = factory.LazyAttribute((lambda talk: f"{talk.uuid}-{slugify(talk.title)}"))
    level = factory.Iterator(TALK_LEVEL, getter=lambda x: x[0])
    abstract_short = factory.Faker("sentence", nb_words=50, variable_nb_words=True)
    abstract_extra = factory.Faker("sentence", nb_words=10, variable_nb_words=True)
    status = factory.Iterator(TALK_STATUS, getter=lambda x: x[0])
    conference = factory.Iterator(
        Conference.objects.all().values_list("code", flat=True)
    )
    language = factory.Iterator(TALK_LANGUAGES, getter=lambda x: x[0])

    @factory.post_generation
    def abstract(self, create, extracted, **kwargs):
        self.setAbstract(
            factory.Faker("sentence", nb_words=30, variable_nb_words=True).generate({})
        )


class SpeakerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Speaker"

    user = factory.SubFactory(auth_factories.UserFactory)


class TalkSpeakerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.TalkSpeaker"

    talk = factory.SubFactory(TalkFactory)
    speaker = factory.SubFactory(SpeakerFactory)


class CommentFactory(factory.DjangoModelFactory):
    class Meta:
        model = "django_comments.Comment"

    comment = factory.Faker("sentence", nb_words=12, variable_nb_words=True)
    site_id = settings.SITE_ID
    content_object = factory.SubFactory(TalkFactory)


class MessageFactory(object):
    subject = factory.Faker(
        "sentence", nb_words=6, variable_nb_words=True, ext_word_list=None
    )
    message = factory.Faker(
        "paragraph", nb_sentences=3, variable_nb_sentences=True, ext_word_list=None
    )


class P3ProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "p3.P3Profile"

    profile = factory.RelatedFactory(AttendeeProfileFactory)


class ScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Schedule"

    # NOTE umgelurgel 22-10-2018
    # This assumes the conference exists which can lead to failures during tests
    # Should be replaced with a get_or_create
    conference = factory.Iterator(
        Conference.objects.all().values_list("code", flat=True)
    )
    slug = factory.LazyAttribute(
        lambda conference: slugify(
            fake.sentence(nb_words=6, variable_nb_words=True)[:50]
        )
    )

    date = factory.Faker("date_time_this_decade", before_now=True, after_now=True)


class P3TalkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "p3.P3Talk"

    talk = factory.SubFactory(TalkFactory)


class TicketConferenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "p3.TicketConference"

    ticket = factory.SubFactory(Ticket)
    diet = factory.Iterator(TICKET_CONFERENCE_DIETS, getter=lambda x: x[0])
    shirt_size = factory.Iterator(TICKET_CONFERENCE_SHIRT_SIZES, getter=lambda x: x[0])


class TrackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Track"

    schedule = factory.SubFactory(ScheduleFactory)

    track = factory.Sequence(lambda x: "track%05d" % x)
    seats = 100


class EventFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Event"

    schedule = factory.SubFactory(ScheduleFactory)
    talk = factory.SubFactory(TalkFactory)
    start_time = factory.LazyFunction(timezone.now)


class EventTrackFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.EventTrack"

    track = factory.SubFactory(TrackFactory)
    event = factory.SubFactory(EventFactory)


class TrackWithEventsFactory(TrackFactory):
    event1 = factory.RelatedFactory(EventTrackFactory, "event")
    event2 = factory.RelatedFactory(EventTrackFactory, "event")
