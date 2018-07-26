# -*- coding: UTF-8 -*-
import datetime
import os.path
from collections import defaultdict, OrderedDict

from conference.models import Conference, AttendeeProfile
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User
from assopy import utils as autils
from p3 import models as p3models
from assopy import models as assopy_models
from conference import models as cmodels

from django.contrib.auth.decorators import user_passes_test

### Decorators


def group_required(*group_names):
    """ Check for group membership before granting access to the view.

        You can pass in one or more group names to the decorator. The
        user has to be member of all listed groups.
    """
    def group_membership_check(user):
        if not user.is_authenticated():
            return False
        if user.is_superuser:
            return True
        return bool(user.groups.filter(name__in=group_names))
    return user_passes_test(group_membership_check)


### Helpers
def assign_ticket_to_user(ticket, user=None):
    """ Assign ticket to the given user (defaults to buyer of the
        ticket if not given).
    """
    if user is None:
        user = ticket.user

    # Get or create the TicketConference record associated with the
    # Ticket
    try:
        p3c = ticket.p3_conference
    except p3models.TicketConference.DoesNotExist:
        p3c = None
    if p3c is None:
        p3c = p3models.TicketConference(ticket=ticket)

    # Set attendee name on the ticket
    ticket.name = ('%s %s' % (user.first_name, user.last_name)).strip()
    ticket.save()

    # Associate the email address with the ticket, if possible
    try:
        check_user = autils.get_user_account_from_email(user.email)
    except User.MultipleObjectsReturned:
        # Use a work-around by setting the .assigned_to to '';
        # this only works if the buyer is the attendee and the
        # user will have other issues in the system as well.
        p3c.assigned_to = ''
    else:
        p3c.assigned_to = user.email

    p3c.save()


def conference_ticket_badge(tickets):
    """See conference.settings.TICKET_BADGE_PREPARE_FUNCTION."""
    conferences = {}
    for c in Conference.objects.all():
        conferences[c.code] = {
            'obj': c,
            'days': c.days(),
        }
    groups = {}
    qs = tickets\
            .select_related('fare', 'p3_conference', 'orderitem__order__user__user')
    for t in qs:
        if t.fare.conference not in groups:
            groups[t.fare.conference] = {
                'name': t.fare.conference,
                'plugin': os.path.join(settings.OTHER_STUFF, 'badge', t.fare.conference, 'conf.py'),
                'tickets': [],
            }
        try:
            p3c = t.p3_conference
        except p3models.TicketConference.DoesNotExist:
            p3c = None
        if p3c is None:
            tagline = ''
            days = '1'
            experience = 0
            badge_image = None
        else:
            tagline = p3c.tagline
            experience = p3c.python_experience
            tdays = map(lambda x: datetime.date(*map(int, x.split('-'))), filter(None, p3c.days.split(',')))
            cdays = conferences[t.fare.conference]['days']
            days = ','.join(map(str,[cdays.index(x)+1 for x in tdays]))
            badge_image = p3c.badge_image.path if p3c.badge_image else None
        if p3c and p3c.assigned_to:
            profile = AttendeeProfile.objects\
                        .select_related('user')\
                        .get(user__email=p3c.assigned_to)
        else:
            profile = t.user.attendeeprofile
        name = t.name.strip()
        if not name:
            if profile.user.first_name or profile.user.last_name:
                name = '%s %s' % (profile.user.first_name, profile.user.last_name)
            else:
                name = t.orderitem.order.user.name()
                if p3c and p3c.assigned_to:
                    name = p3c.assigned_to + ' (%s)' % name
        groups[t.fare.conference]['tickets'].append({
            'name': name,
            'tagline': tagline,
            'days': days,
            'fare': {
                'code': t.fare.code,
                'type': t.fare.recipient_type,
            },
            'experience': experience,
            'badge_image': badge_image,
            'staff': t.ticket_type == 'staff',
            'profile-link': settings.DEFAULT_URL_PREFIX + reverse(
                'conference-profile-link', kwargs={'uuid': profile.uuid}),
        })
    return groups.values()


def gravatar(email, size=80, default='identicon', rating='r', protocol='https'):
    import urllib, hashlib

    if protocol == 'https':
        host = 'https://secure.gravatar.com'
    else:
        host = 'http://www.gravatar.com'
    gravatar_url = host + "/avatar/" + hashlib.md5(email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode({
        'default': default,
        'size': size,
        'rating': rating,
    })
    return gravatar_url

def spam_recruiter_by_conf(conf):
    """ Return a queryset with the User who have agreed to be
    contacted via email for the purpose of recruiting."""
    from django.contrib.auth.models import User

    tickets = settings.CONFERENCE_TICKETS(conf, ticket_type='conference')
    owned = tickets.filter(p3_conference__assigned_to='')
    assigned = tickets.exclude(p3_conference__assigned_to='')

    first_run = User.objects\
        .filter(\
            id__in=owned.values('user'),\
            attendeeprofile__p3_profile__spam_recruiting=True)

    second_run = User.objects\
        .filter(\
            email__in=assigned.values('p3_conference__assigned_to'),\
            attendeeprofile__p3_profile__spam_recruiting=True)
    return first_run | second_run


from django.core.cache import cache
from django.utils.http import urlquote
from hashlib import md5 as md5_constructor

def template_cache_name(fragment_name, *variables):
    args = md5_constructor(u':'.join([urlquote(var) for var in variables]))
    return 'template.cache.%s.%s' % (fragment_name, args.hexdigest())

def invalidate_template_cache(fragment_name, *variables):
    args = md5_constructor(u':'.join([urlquote(var) for var in variables]))
    cache_key = 'template.cache.%s.%s' % (fragment_name, args.hexdigest())
    cache.delete(cache_key)
    return

def conference2ical(conf, user=None, abstract=False):
    from conference import dataaccess
    from conference import models as cmodels
    from datetime import timedelta

    curr = cmodels.Conference.objects.current()
    try:
        hotel = cmodels.SpecialPlace.objects.get(type='conf-hq')
    except cmodels.SpecialPlace.DoesNotExist:
        hotel = None
    else:
        if not hotel.lat or not hotel.lng:
            hotel = None

    def altf(data, component):
        if component == 'calendar':
            if user is None:
                url = reverse('p3-schedule', kwargs={'conference': conf})
            else:
                url = reverse('p3-schedule-my-schedule', kwargs={'conference': conf})
            data['uid'] = settings.DEFAULT_URL_PREFIX + url
            if curr.code == conf:
                data['ttl'] = timedelta(seconds=3600)
            else:
                data['ttl'] = timedelta(days=365)
        elif component == 'event':
            eid = data['uid']
            data['uid'] = settings.DEFAULT_URL_PREFIX + '/p3/event/' + str(data['uid'])
            data['organizer'] = ('mailto:info@europython.eu', {'CN': 'EuroPython'})
            if hotel:
                data['coordinates'] = [hotel.lat, hotel.lng]
            if not isinstance(data['summary'], tuple):
                # this is a custom event, if it starts with an anchor I can
                # extract the reference
                import re
                m = re.match(r'<a href="(.*)">(.*)</a>', data['summary'])
                if m:
                    url = m.group(1)
                    if url.startswith('/'):
                        url = settings.DEFAULT_URL_PREFIX + url
                    data['summary'] = (m.group(2), {'ALTREP': url})
            if abstract:
                e = dataaccess.event_data(eid)
                if e['talk']:
                    from conference.templatetags.conference import name_abbrv
                    speakers = [ name_abbrv(s['name']) for s in e['talk']['speakers'] ]
                    speakers = ", ".join(speakers)
                    data['summary'] = (data['summary'][0] + ' by ' + speakers, data['summary'][1])
                ab = e['talk']['abstract'] if e['talk'] else e['abstract']
                data['description'] = ab
        return data
    if user is None:
        from conference.utils import conference2ical as f
        cal = f(conf, altf=altf)
    else:
        from conference.utils import TimeTable2
        from conference.utils import timetables2ical as f

        qs = cmodels.Event.objects\
            .filter(eventinterest__user=user, eventinterest__interest__gt=0)\
            .filter(schedule__conference=conf)\
            .values('id', 'schedule')

        events = defaultdict(list)
        for x in qs:
            events[x['schedule']].append(x['id'])

        sids = sorted(events.keys())
        timetables = [ TimeTable2.fromEvents(x, events[x]) for x in sids ]
        cal = f(timetables, altf=altf)
    return cal


# Database access helpers

def clean_title(title):
    """ Clean a talk title. """
    title = title.strip()
    if not title:
        return title

    # Remove whitespace
    title = title.strip()
    # Remove double spaces
    title = title.replace("  ", " ")
    # Remove quotes
    if title[0] == '"' and title[-1] == '"':
        title = title[1:-1]
    return title


def talk_title(talk):
    """ Return a clean talk title given a Talk. """
    # Remove whitespace
    title = talk.title.strip()
    return clean_title(title)


def profile_url(user):
    """ Return the URL of the user profile. """
    return reverse('conference-profile', args=[user.attendeeprofile.slug])


def talk_schedule(talk):
    """ Return the list of timeslots when the talk is scheduled."""
    slots = []
    events = talk.event_set.all()
    for event in events:
        timerange = event.get_time_range()
        slot = '{}, {}'.format(str(timerange[0]), str(timerange[1]))
        slots.append(slot)
    return slots


def talk_type(talk):
    """ Return the pretty name for the type of the talk."""
    if talk.admin_type:
        typ = talk.get_admin_type_display()
    else:
        typ = talk.get_type_display()
    return typ


def group_talks_by_type(talks):
    """ Return a dict with lists of talks grouped by the type of talk."""
    type_talks = defaultdict(list)
    for talk in talks:
        type_talks[talk_type(talk)].append(talk)

    return type_talks


def group_all_talks_by_admin_type(conference, talk_status='accepted'):
        """ Return a dict with the talks for the `conference`
        with status `talk_status` separated by administrative type. """
        # Group by admin types
        talks = OrderedDict()
        for adm_type, type_name in dict(cmodels.TALK_ADMIN_TYPE).items():
            talks[type_name] = list(cmodels.Talk.objects
                                    .filter(conference=conference,
                                            status=talk_status,
                                            admin_type=adm_type))

        type_groups = {'talk':        ['t_30', 't_45', 't_60'],
                       'interactive': ['i_60'],
                       'training':    ['r_180'],
                       'panel':       ['p_60', 'p_90'],
                       'poster':      ['p_180'],
                       'helpdesk':    ['h_180'],
                      }

        for grp_name, grp_types in type_groups.items():
            grp_talks = []
            for talk_type in grp_types:
                bag = list(cmodels.Talk.objects
                           .filter(conference=conference,
                                   status=talk_status,
                                   type=talk_type,
                                   admin_type=''))
                grp_talks.extend(bag)

            talks[grp_name] = grp_talks

        return talks


def speaker_listing(talk):
    """ Return a list of the speakers' names of the talk."""
    return [u'{} {}'.format(speaker.user.first_name, speaker.user.last_name)
            for speaker in talk.get_all_speakers()]


def speaker_emails(talk):
    """ Return a list of the speakers' emails of the talk."""
    return [u'{}'.format(speaker.user.email) for speaker in talk.get_all_speakers()]


def speaker_twitters(talk):
    """ Return a list of the speakers' twitter handles of the talk."""
    return [u'@{}'.format(speaker.user.attendeeprofile.p3_profile.twitter)
            for speaker in talk.get_all_speakers()]


def get_all_order_tickets(conference=settings.CONFERENCE_CONFERENCE):
    """ Return all valid conference tickets for the conference."""
    def conference_year(conference):
        return conference[-2:]

    year = conference_year(conference)

    orders = assopy_models.Order.objects.filter(_complete=True)
    conf_orders = (order for order in orders if order.code.startswith('O/{}.'.format(year)))
    tickets = (
        ordi.ticket for order in conf_orders
        for ordi in order.orderitem_set.all()
        if ordi.ticket is not None
    )
    conf_order_tkts = [tk for tk in tickets if is_valid_ticket(tk, conference)]
    return conf_order_tkts


def get_orders_from(user):
    """ Return the list of complete orders made by the user. """
    return assopy_models.Order.objects.filter(_complete=True, user=user.id)


def get_tickets_assigned_to(user):
    """ Return the list of tickets assigned to the user. """
    return p3models.TicketConference.objects.filter(assigned_to=user.email)


def is_ticket_assigned_to_someone_else(ticket, user):
    """ Return False if the ticket is assigned to the user, True otherwise."""
    tickets = p3models.TicketConference.objects.filter(ticket_id=ticket.id)

    if not tickets:
        raise AttributeError('Could not find any ticket with id '
                             '{}.'.format(ticket.id))

    if len(tickets) > 1:
        raise RuntimeError('Got more than one ticket from a ticket_id.'
                           'Tickets obtained: {}.'.format(tickets))

    tkt = tickets[0]
    if tkt.ticket.user_id != user.id:
        return True

    if not tkt.assigned_to:
        return False

    if tkt.assigned_to == user.email:
        return False
    else:
        return True


def is_valid_ticket(ticket, conference_name):
    """ Return True if the ticket is a valid conference ticket for the
    given conference.
    """
    tickets = cmodels.Ticket.objects.filter(id=ticket.id,
                                            fare__conference=conference_name,
                                            fare__ticket_type='conference',
                                            orderitem__order___complete=True,
                                            frozen=False,)
    return bool(tickets)


def has_ticket(user, conference_name):
    """ Return True if the user has any valid ticket assigned to him,
    False otherwise."""
    tickets = get_tickets_assigned_to(user)
    if tickets:
        return True

    user_tickets = list(user.ticket_set.all())
    orders = get_orders_from(user)
    if orders:
        order_tkts = [ordi.ticket
                      for order in orders
                      for ordi in order.orderitem_set.all()
                      if ordi.ticket is not None]
        user_tickets.extend(order_tkts)

    for tkt in user_tickets:
        if is_valid_ticket(tkt, conference_name) and \
         not is_ticket_assigned_to_someone_else(tkt, user):
            return True

    return False


def have_tickets(talk, conference_name):
    """ Return True if all speakers of the talk have a ticket,
    False otherwise.
    """
    usrs = talk.get_all_speakers()
    return [has_ticket(user.user, conference_name) for user in usrs]


def talk_track_title(talk):
    """ Return a list of the tracks when the talk is scheduled. """
    event = talk.get_event()
    if not event:
        return []
    return [tr.title for tr in event.tracks.all()]


def talk_votes(talk):
    """ Return a dict[user_id: n_votes] for the given talk."""
    qs = cmodels.VotoTalk.objects.filter(talk=talk.id).all()
    user_votes = []
    for v in qs:
        user_votes.append({v.user_id: v.vote})
    return user_votes


def speaker_companies(talk):
    """ Return a set of the companies of the speakers of the talk."""
    companies = sorted(
        set(speaker.user.attendeeprofile.company
            for speaker in talk.speakers.all()
                if speaker.user.attendeeprofile))
    return companies


def get_profile_company(profile):
    """ Return a (title, company) to generate a textual profile for the user.
    Since users sometimes use Company and Tag with the same content.
    """
    title = ''
    company = ''
    if profile.job_title and profile.company:
        if profile.company.lower().strip() in profile.job_title.lower().strip():
            title = ''
            company = profile.job_title
        else:
            title = profile.job_title
            company = profile.company
    elif profile.job_title:
        title = profile.job_title
    elif profile.company:
        company = profile.company

    return title, company
