
from pytest import mark

from django.urls import reverse

from tests.factories import (
    ConferenceFactory, ConferenceTagFactory, EventFactory, ScheduleFactory, TrackFactory,
)


# /admin/conference/conference/<cid>/schedule/  conference.admin.schedule_view
@mark.django_db
def test_conference_schedule_admin(admin_client):
    conference = ConferenceFactory()
    url = reverse('admin:conference-conference-schedule', kwargs={'cid': conference.code})

    response = admin_client.get(url)

    assert response.status_code == 200


# /admin/conference/conference/<cid>/schedule/<sid>/<tid>/  conference.admin.schedule_view_track
@mark.django_db
def test_conference_schedule_track_admin(admin_client):
    conference = ConferenceFactory(code='epbeta')
    schedule = ScheduleFactory(conference=conference)
    track = TrackFactory(schedule=schedule)
    url = reverse('admin:conference-conference-schedule-track', kwargs={
        'cid': track.schedule.conference,
        'sid': track.schedule.id,
        'tid': track.id,
    })

    response = admin_client.get(url)

    assert response.status_code == 200


# /admin/conference/conference/<cid>/stats/ conference.admin.stats_list
@mark.django_db
def test_conference_ticket_stats_admin(admin_client):
    conference = ConferenceFactory()
    url = reverse('admin:conference-ticket-stats', kwargs={'cid': conference.code})

    response = admin_client.get(url)

    assert response.status_code == 200


# /admin/conference/conference/<cid>/stats/details  conference.admin.stats_details
@mark.django_db
def test_conference_ticket_stats_details_admin(admin_client):
    conference = ConferenceFactory()
    url = reverse('admin:conference-ticket-stats-details', kwargs={'cid': conference.code})

    response = admin_client.get(url, data={'code': '1.2'})

    assert response.status_code == 200


# /admin/conference/speaker/stats/list/ conference.admin.stats_list
@mark.django_db
def test_conference_speaker_stat_list_admin(admin_client):
    url = reverse('admin:conference-speaker-stat-list')

    response = admin_client.get(url)

    assert response.status_code == 200


# /admin/conference/conferencetag/merge/  conference.admin.merge_tags
@mark.django_db
def test_conference_tag_merge_admin(admin_client):
    tags = ConferenceTagFactory.create_batch(3)
    tag_ids = [tag.id for tag in tags]
    url = reverse('admin:conference-conferencetag-merge')

    response = admin_client.get(url, data={'tags': tag_ids})

    assert response.status_code == 200


# /admin/conference/schedule/<sid>/events/<eid> conference.admin.event
@mark.django_db
def test_conference_schedule_event_detail_admin(admin_client):
    conference = ConferenceFactory()
    event = EventFactory(schedule__conference=conference)
    url = reverse('admin:conference-schedule-event', kwargs={
        'sid': event.schedule.id,
        'eid': event.id,
    })

    response = admin_client.get(url)

    assert response.status_code == 200


# /admin/conference/schedule/<sid>/tracks/<tid> conference.admin.tracks
@mark.django_db
def test_conference_schedule_tracks_admin(admin_client):
    conference = ConferenceFactory()
    schedule = ScheduleFactory(conference=conference)
    track = TrackFactory(schedule=schedule)
    url = reverse('admin:conference-schedule-tracks', kwargs={
        'sid': schedule.id,
        'tid': track.id,
    })

    response = admin_client.get(url)

    assert response.status_code == 200


# /admin/conference/schedule/stats/ conference.admin.expected_attendance
@mark.django_db
def test_conference_schedule_expected_attendance_admin(admin_client):
    url = reverse('admin:conference-schedule-expected_attendance')

    response = admin_client.get(url)

    assert response.status_code == 200
