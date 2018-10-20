import factory
from django.template.defaultfilters import slugify

from conference.models import Conference

from faker import Faker
fake = Faker()

class ScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Schedule'

    # NOTE umgelurgel 22-10-2018
    # This assumes the conference exists which can lead to failures during tests
    # Should be replaced with a get_or_create
    conference = factory.Iterator(
        Conference.objects.all().values_list('code', flat=True)
    )
    slug = factory.LazyAttribute(lambda conference: slugify(fake.sentence(nb_words=6, variable_nb_words=True)[:50]))

    date = factory.Faker('date_time_this_decade', before_now=True, after_now=True)