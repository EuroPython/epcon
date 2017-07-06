import factory
from django.template.defaultfilters import slugify

from conference.models import Conference

from faker import Faker
fake = Faker()

class ScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Schedule'

    conference = factory.Iterator(
        Conference.objects.all().values_list('code', flat=True)
    )
    slug = factory.LazyAttribute(lambda conference: slugify(fake.sentence(nb_words=6, variable_nb_words=True)))

    date = factory.Faker('date_time_this_decade', before_now=True, after_now=True)