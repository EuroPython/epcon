from datetime import datetime

import pickle

from django.contrib.auth import get_user_model
from django.db import transaction

from assopy.models import AssopyUser
from conference.models import AttendeeProfile, Conference, Speaker, Talk, TalkSpeaker
from conference.cfp import validate_tags

User = get_user_model()

start_dt = datetime(2019, 4, 25, 9, 17, 53)
end_dt = datetime(2019, 4, 25, 15, 56)


def get_users():
    users = []
    for user in User.objects.filter(date_joined__gte=start_dt, date_joined__lte=end_dt):
        user_dict = {
            'password': user.password,
            'is_superuser': user.is_superuser,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'email': user.email,
            'is_staff': user.is_staff,
            'is_active': user.is_active,
            'date_joined': user.date_joined,
            'username': user.username,
            'assopy_user': {
                'token': user.assopy_user.token,
                'assopy_id': user.assopy_user.assopy_id,
                'card_name': user.assopy_user.card_name,
                'vat_number': user.assopy_user.vat_number,
                'cf_code': user.assopy_user.cf_code,
                'address': user.assopy_user.address,
            },
            'attendee_profile': {
                'slug': user.attendeeprofile.slug,
                'uuid': user.attendeeprofile.uuid,
                # skipping image
                'birthday': user.attendeeprofile.birthday,
                'is_minor': user.attendeeprofile.is_minor,
                'phone': user.attendeeprofile.phone,
                'gender': user.attendeeprofile.gender,
                'personal_homepage': user.attendeeprofile.personal_homepage,
                'company': user.attendeeprofile.company,
                'company_homepage': user.attendeeprofile.company_homepage,
                'job_title': user.attendeeprofile.job_title,
                'location': user.attendeeprofile.location,
                'visibility': user.attendeeprofile.visibility,
                # bio field is assigned using the setBio() method
                'bio_body': user.attendeeprofile.getBio() and user.attendeeprofile.getBio().body or None,
            },
        }

        if user.assopy_user.country:
            user_dict['assopy_user']['country_iso'] = user.assopy_user.country.iso
        else:
            user_dict['assopy_user']['country'] = None

        users.append(user_dict)

    return users


def get_talks():
    talks = []
    for talk in Talk.objects.filter(created__gte=start_dt, created__lte=end_dt):
        talk_dict = {
            'uuid': talk.uuid,
            'title': talk.title,
            'sub_title': talk.sub_title,
            'slug': talk.slug,
            'prerequisites': talk.prerequisites,
            # skipping conference since it's obvious
            'admin_type': talk.admin_type,
            'language': talk.language,
            'abstract_short': talk.abstract_short,
            'abstract_extra': talk.abstract_extra,
            # Skipping slides and video fields
            'status': talk.status,
            'level': talk.level,
            'training_available': talk.training_available,
            'type': talk.type,
            'domain': talk.domain,
            'domain_level': talk.domain_level,
            'duration': talk.duration,
            'suggested_tags': talk.suggested_tags,
            'created': talk.created,
            'modified': talk.modified,

            # fields that require some processing before ssignment
            'created_by_email': talk.created_by.email,
            'abstract_body': talk.getAbstract() and talk.getAbstract().body or None,
            # m2m fields
            'speaker_emails': [x.user.email for x in talk.speakers.all()],
            'tags_names': [x.name for x in talk.tags.all()],
        }

        talks.append(talk_dict)

    return talks


def save_dict(data_dict, filename):
    with open(filename, 'wb') as pickle_file:
        pickle.dump(data_dict, pickle_file)


def read_dict(filename):
    with open(filename, 'rb') as pickle_file:
        data_dict = pickle.load(pickle_file)

    return data_dict


def restore_users(users):
    for user in users:
        if User.objects.filter(email=user['email']).exists():
            print('Skipping user creation: {}.'.format(user['email']))
            continue

        django_user = User.objects.create_user(
            is_superuser=user['is_superuser'],
            first_name=user['first_name'],
            last_name=user['last_name'],
            email=user['email'],
            is_staff=user['is_staff'],
            is_active=user['is_active'],
            date_joined=user['date_joined'],
            username=user['username'],
            # This is equivalent to calling user.set_unusable_password
            password=None,
        )
        django_user.password = user['password']
        django_user.save()

        assopy_user = AssopyUser(
            user=django_user,
            token=user['assopy_user']['token'],
            assopy_id=user['assopy_user']['assopy_id'],
            card_name=user['assopy_user']['card_name'],
            vat_number=user['assopy_user']['vat_number'],
            cf_code=user['assopy_user']['cf_code'],
            address=user['assopy_user']['address'],
        )
        assopy_user.save()

        profile = AttendeeProfile(
            user=django_user,
            slug=user['attendee_profile']['slug'],
            uuid=user['attendee_profile']['uuid'],
            birthday=user['attendee_profile']['birthday'],
            is_minor=user['attendee_profile']['is_minor'],
            phone=user['attendee_profile']['phone'],
            gender=user['attendee_profile']['gender'],
            personal_homepage=user['attendee_profile']['personal_homepage'],
            company=user['attendee_profile']['company'],
            company_homepage=user['attendee_profile']['company_homepage'],
            job_title=user['attendee_profile']['job_title'],
            location=user['attendee_profile']['location'],
            visibility=user['attendee_profile']['visibility'],
        )
        profile.save()

        if user['attendee_profile']['bio_body']:
            profile.setBio(user['attendee_profile']['bio_body'])
            profile.save()

        print('User created: {}.'.format(user['email']))


def restore_talks(talks):
    for talk in talks:
        if Talk.objects.filter(title=talk['title']).exists():
            print('Skipping talk creation: {}.'.format(talk['title']))
            continue

        talk_author = User.objects.filter(email=talk['created_by_email'])
        if talk_author.count() != 1:
            print('Cannot identify the author of talk {}'.format(talk['title']))
            continue

        talk_author = talk_author.first()

        conference_talk = Talk(
            uuid=talk['uuid'],
            title=talk['title'],
            sub_title=talk['sub_title'],
            slug=talk['slug'],
            prerequisites=talk['prerequisites'],
            admin_type=talk['admin_type'],
            language=talk['language'],
            abstract_short=talk['abstract_short'],
            abstract_extra=talk['abstract_extra'],
            status=talk['status'],
            level=talk['level'],
            training_available=talk['training_available'],
            type=talk['type'],
            domain=talk['domain'],
            domain_level=talk['domain_level'],
            duration=talk['duration'],
            suggested_tags=talk['suggested_tags'],
            created=talk['created'],
            modified=talk['modified'],
        )
        conference_talk.created_by = talk_author
        conference_talk.conference = Conference.objects.current().code
        conference_talk.save()
        if talk['abstract_body']:
            conference_talk.setAbstract(talk['abstract_body'])
        if talk['tags_names']:
            conference_talk.tags.set(*validate_tags(talk['tags_names']))
        conference_talk.save()

        speaker, _ = Speaker.objects.get_or_create(user=talk_author)
        TalkSpeaker.objects.get_or_create(talk=conference_talk, speaker=speaker)

        print('Talk created: {}'.format(conference_talk.title))


def restore_data(users_file, talks_file):
    users = read_dict(users_file)
    talks = read_dict(talks_file)

    with transaction.atomic():
        restore_users(users)
        restore_talks(talks)
