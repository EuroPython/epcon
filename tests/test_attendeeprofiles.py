
"""
TODO(artcz)(2019-01-09) - Filename WIP
"""

from django.urls import reverse

from conference.models import ATTENDEEPROFILE_VISIBILITY

from tests.common_tools import make_user


def test_865_attendee_profile_editable_in_django_admin(admin_client):
    LONG_RANDOM_SLUG = 'very-long-and-complicated-slug'

    ap_admin_list_url = reverse('admin:conference_attendeeprofile_changelist')
    response = admin_client.get(ap_admin_list_url)
    assert LONG_RANDOM_SLUG not in response.content.decode()

    user = make_user()
    # some weird format with ranodm letters and digits not uuid{4,5}
    assert len(user.attendeeprofile.uuid) == 6

    ap = user.attendeeprofile
    ap.slug = LONG_RANDOM_SLUG
    ap.save()

    response = admin_client.get(ap_admin_list_url)
    assert LONG_RANDOM_SLUG in response.content.decode()

    ap_edit_url = reverse(
        'admin:conference_attendeeprofile_change',
        # user.id because AttendeeProfile doesn't have it's own primary_key,
        # just OneToOneField to User
        args=[user.id],
    )
    assert ap_edit_url in response.content.decode()

    response = admin_client.post(ap_edit_url, {
        'slug': 'different-slug',
        'uuid': '12345',
        'user': user.id,
        'visibility': ATTENDEEPROFILE_VISIBILITY.PRIVATE,
    })
    EDIT_OK_302 = 302
    assert response.status_code == EDIT_OK_302

    ap.refresh_from_db()
    assert ap.slug == 'different-slug'
    assert ap.uuid == '12345'
