import functools
import random
import uuid
from datetime import timedelta
from random import randint

import factory
import factory.django
from faker import Faker

from django.conf import settings
from django.template.defaultfilters import slugify
from django.utils import timezone

from assopy.models import Vat, VatFare
from conference.models import (
    AttendeeProfile,
    Conference,
    Fare,
    News,
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

    username = factory.LazyAttribute(lambda o: fake.user_name())
    password = factory.PostGenerationMethodCall("set_password", "password123")
    first_name = factory.LazyAttribute(lambda o: fake.first_name())
    last_name = factory.LazyAttribute(lambda o: fake.last_name())
    email = factory.LazyAttribute(lambda o: fake.safe_email())
    is_active = True

    assopy_user = factory.RelatedFactory("tests.factories.AssopyUserFactory", "user")
    attendeeprofile = factory.RelatedFactory("tests.factories.AttendeeProfileFactory", "user")


class AssopyUserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.AssopyUser"

    user = factory.SubFactory(
        UserFactory, assopy_user=factory.LazyAttribute(lambda assopy_user: assopy_user)
    )


class AttendeeProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.AttendeeProfile"

    user = factory.SubFactory(UserFactory)
    slug = factory.LazyAttribute(
        lambda o: slugify("{} {}".format(o.user.first_name, o.user.last_name))
    )
    gender = "x"

    @factory.lazy_attribute
    def uuid(self):
        return AttendeeProfile.objects.randomUUID(6)

    birthday = factory.LazyAttribute(
        lambda o: fake.date_between(start_date='-50y', end_date='-15y')
    )


class CountryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Country"
        django_get_or_create = ('iso',)

    iso = factory.Faker("country_code")
    name = factory.Faker("country")


class VatFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "assopy.Vat"

    value = 20


class FareFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Fare"
        django_get_or_create = ('conference', 'code')

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
        return "%s – %s" % (settings.CONFERENCE_NAME, ALL_POSSIBLE_FARE_CODES[self.code])

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

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """
        Override the default ``_create`` in order to be able to pass order_type to the factory;
        The manager's ``create`` does not accept order_type as an argument.
        """
        order_type = kwargs.pop('order_type', None)
        manager = cls._get_manager(model_class)
        instance = manager.create(*args, **kwargs)

        if order_type:
            instance.order_type = order_type
            instance.save()

        if not instance.uuid:
            instance.uuid = str(uuid.uuid4())
            instance.save()

        return instance


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
        django_get_or_create = ('code',)

    name = settings.CONFERENCE_NAME
    code = settings.CONFERENCE_CONFERENCE

    conference_start = factory.LazyAttribute(lambda obj: timezone.now() + timedelta(days=30))
    conference_end = factory.LazyAttribute(lambda obj: obj.conference_start + timedelta(days=5))
    cfp_start = factory.LazyAttribute(lambda obj: obj.conference_start - timedelta(days=33))
    cfp_end = factory.LazyAttribute(lambda obj: obj.cfp_start + timedelta(days=6))
    # During a real conference, voting would start after the cfp ends, not run concurrently.
    # The opposite is the case here to make testing easier.
    voting_start = factory.LazyAttribute(lambda obj: obj.cfp_start)
    voting_end = factory.LazyAttribute(lambda obj: obj.cfp_end)


class TicketFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.Ticket"

    user = factory.SubFactory(UserFactory)
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

    user = factory.SubFactory(UserFactory)


class TalkSpeakerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.TalkSpeaker"

    talk = factory.SubFactory(TalkFactory)
    speaker = factory.SubFactory(SpeakerFactory)


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


class NewsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "conference.News"

    conference = factory.Iterator(Conference.objects.all())
    title = factory.Faker('sentence', nb_words=4)
    content = factory.Faker('sentence', nb_words=20)
    status = News.STATUS.PUBLISHED
    published_date = factory.LazyFunction(timezone.now)
