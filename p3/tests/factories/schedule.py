import factory

from conference.models import Conference


class ScheduleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'conference.Schedule'

    conference = factory.Iterator(
        Conference.objects.all().values_list('code', flat=True)
    )

    date = factory.Faker('date_time_this_decade', before_now=True, after_now=True)