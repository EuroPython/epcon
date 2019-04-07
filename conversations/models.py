import uuid

from django.db import models
from django.contrib.auth.models import User

from model_utils import Choices
from model_utils.models import TimeStampedModel

from conference.models import Conference


class Thread(TimeStampedModel):

    CATEGORIES = Choices(
        ('HELPDESK', 'HELPDESK'),
        ('FINAID',   'FINAID'),
        ('SPONSORS', 'SPONSORS'),
    )

    STATUS = Choices(
        (0, 'NEW',     'New'),
        (1, 'REOPENED', 'Reopened'),
        (2, 'WAITING', 'Waiting'),
        (3, 'STAFF_REPLIED', 'Staff Replied'),
        (4, 'USER_REPLIED',  'User Replied'),
        (5, 'COMPLETED',     'Completed'),
    )

    # TODO(artcz): Maybe this needs str field, especially if we want shortuuid?
    # + limitations of sqlite, dunno if binary uuid field exists there.
    # + maybe we could use ordered uuid?

    uuid = models.UUIDField()
    created_by = models.ForeignKey(User)
    conference = models.ForeignKey(Conference)

    title = models.CharField(max_length=255)
    category = models.CharField(max_length=20, choices=CATEGORIES)
    status = models.IntegerField(choices=STATUS)

    # This is denormalisation to speed up ordering by last activity
    last_message_date = models.DateTimeField()

    class Meta:
        ordering = ['-last_message_date', 'created']

    def __str__(self):
        return f'Thread(uuid={self.uuid}, title={self.title})'


class Message(TimeStampedModel):

    uuid = models.UUIDField(unique=True)
    created_by = models.ForeignKey(User)
    is_staff_reply = models.BooleanField(default=False)

    thread = models.ForeignKey(Thread)
    content = models.TextField()

    def __str__(self):
        return 'Message(uuid={self.uuid})'


class Attachment(TimeStampedModel):
    uuid = models.UUIDField(default=uuid.uuid4())

    # we use uuid here so we can upload attachments independently of when we
    # save the message, backfilled after upload through internal API.
    message = models.ForeignKey(
        Message,
        to_field='uuid',
        blank=True,
        null=True,
    )

    # TODO: upload_to with uuid4 filename to a SR uuid directory
    file = models.FileField()

    def __str__(self):
        return f'Attachment(uuid={self.uuid}, filename={self.file.name})'
