from django import forms
from django import http
from django.conf import settings
from django.core.urlresolvers import reverse
from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth.models import User

from assopy import utils as autils
from conference import admin as cadmin
from conference import models as cmodels
from p3 import models
from p3 import dataaccess
from p3 import utils

from taggit.forms import TagField
from taggit_labels.widgets import LabelWidget


#TODO: This monstrosity created a joint modelform for Ticket and TicketConference instances.
#TODO: Use inline form for the one to one relationship or merge the models.
_TICKET_CONFERENCE_COPY_FIELDS = ('shirt_size', 'python_experience', 'diet', 'tagline', 'days', 'badge_image')
def ticketConferenceForm():
    class _(forms.ModelForm):
        class Meta:
            model = models.TicketConference
            fields = '__all__'

    fields = _().fields

    class TicketConferenceForm(forms.ModelForm):
        shirt_size = fields['shirt_size']
        python_experience = fields['python_experience']
        diet = fields['diet']
        tagline = fields['tagline']
        days = fields['days']
        badge_image = fields['badge_image']

        class Meta:
            model = cmodels.Ticket
            fields = '__all__'

        def __init__(self, *args, **kw):
            if 'instance' in kw:
                o = kw['instance']
                try:
                    p3c = o.p3_conference
                except models.TicketConference.DoesNotExist:
                    pass
                else:
                    if p3c:
                        initial = kw.pop('initial', {})
                        for k in _TICKET_CONFERENCE_COPY_FIELDS:
                            initial[k] = getattr(p3c, k)
                        kw['initial'] = initial
            return super().__init__(*args, **kw)

    return TicketConferenceForm


class TicketConferenceAdmin(cadmin.TicketAdmin):
    list_display = cadmin.TicketAdmin.list_display + (
        'frozen',
        '_order',
        '_order_date',
        '_assigned',
        '_shirt_size',
        '_diet',
        '_python_experience',
        #'_tagline',
        )
    list_select_related = True
    list_filter = cadmin.TicketAdmin.list_filter + (
        'fare__code',
        'orderitem__order___complete',
        'frozen',
        'p3_conference__shirt_size',
        'p3_conference__diet',
        'p3_conference__python_experience',
        'orderitem__order__created',
        )
    search_fields = cadmin.TicketAdmin.search_fields + (
        'orderitem__order__code',
        'fare__code',
        )
    actions = (
        'do_assign_to_buyer',
        'do_update_ticket_name',
        )
    form = ticketConferenceForm()

    def _order(self, obj):
        url = reverse('admin:assopy_order_change',
                      args=(obj.orderitem.order.id,))
        return '<a href="%s">%s</a>' % (url, obj.orderitem.order.code)
    _order.allow_tags = True

    def _order_date(self, o):
        return o.orderitem.order.created
    _order_date.admin_order_field = 'orderitem__order__created'

    def _assigned(self, ticket):
        if ticket.p3_conference:
            assigned_to = ticket.p3_conference.assigned_to
            if assigned_to:
                comment = ''
                user = None
                try:
                    user = autils.get_user_account_from_email(assigned_to)
                except User.MultipleObjectsReturned:
                    comment = ' (email not unique)'
                except User.DoesNotExist:
                    try:
                        user = autils.get_user_account_from_email(assigned_to,
                                                                  active_only=False)
                    except User.DoesNotExist:
                        comment = ' (does not exist)'
                    else:
                        comment = ' (user inactive)'
                if user is not None:
                    url = reverse('admin:auth_user_change', args=(user.id,))
                    user_name = ('%s %s' %
                                 (user.first_name, user.last_name)).strip()
                    if not user_name:
                        user_name = assigned_to
                        comment += ' (no name set)'
                    return '<a href="%s">%s</a>%s' % (url, user_name, comment)
                elif not comment:
                    comment = ' (missing user account)'
                return '%s%s' % (assigned_to, comment)
            else:
                return '(not assigned)'
        else:
            return '(old style ticket)'
    _assigned.allow_tags = True
    _assigned.admin_order_field = 'p3_conference__assigned_to'

    def do_assign_to_buyer(self, request, queryset):

        if not queryset:
            self.message_user(request, 'no tickets selected', level='error')
            return
        for ticket in queryset:
            # Assign to buyer
            utils.assign_ticket_to_user(ticket, ticket.user)

    do_assign_to_buyer.short_description = 'Assign to buyer'

    def do_update_ticket_name(self, request, queryset):

        if not queryset:
            self.message_user(request, 'no tickets selected')
            return
        for ticket in queryset:
            # Find selected user
            if not ticket.p3_conference:
                continue
            assigned_to = ticket.p3_conference.assigned_to
            try:
                user = autils.get_user_account_from_email(assigned_to)
            except User.MultipleObjectsReturned:
                self.message_user(request,
                                  'found multiple users with '
                                  'email address %s' % assigned_to,
                                  level='error')
                return
            except User.DoesNotExist:
                self.message_user(request,
                                  'no user record found or user inactive for '
                                  ' email address %s' % assigned_to,
                                  level='error')
                return
            if user is None:
                self.message_user(request,
                                  'no user record found for '
                                  ' email address %s' % assigned_to,
                                  level='error')
            # Reassign to selected user
            utils.assign_ticket_to_user(ticket, user)

    do_update_ticket_name.short_description = 'Update ticket name'

    def _shirt_size(self, o):
        try:
            p3c = o.p3_conference
        except models.TicketConference.DoesNotExist:
            return ''
        return p3c.shirt_size

    def _diet(self, o):
        try:
            p3c = o.p3_conference
        except models.TicketConference.DoesNotExist:
            return ''
        return p3c.diet

    def _python_experience(self, o):
        try:
            p3c = o.p3_conference
        except models.TicketConference.DoesNotExist:
            return ''
        return p3c.python_experience
    _python_experience.admin_order_field = 'p3_conference__python_experience'

    def _tagline(self, o):
        try:
            p3c = o.p3_conference
        except models.TicketConference.DoesNotExist:
            return ''
        html = p3c.tagline
        if p3c.badge_image:
            i = ['<img src="%s" width="24" />' % p3c.badge_image.url] * p3c.python_experience
            html += '<br />' + ' '.join(i)
        return html
    _tagline.allow_tags = True

    def save_model(self, request, obj, form, change):
        obj.save()
        try:
            p3c = obj.p3_conference
        except models.TicketConference.DoesNotExist:
            p3c = None
        if p3c is None:
            p3c = models.TicketConference(ticket=obj)

        data = form.cleaned_data
        for k in _TICKET_CONFERENCE_COPY_FIELDS:
            setattr(p3c, k, data.get(k))
        p3c.save()

    def changelist_view(self, request, extra_context=None):
        if not request.GET:
            q = request.GET.copy()
            q['fare__conference'] = settings.CONFERENCE_CONFERENCE
            q['fare__ticket_type__exact'] = 'conference'
            q['orderitem__order___complete__exact'] = 1
            q['frozen__exact'] = 0
            request.GET = q
            request.META['QUERY_STRING'] = request.GET.urlencode()
        return super().changelist_view(request, extra_context=extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('orderitem__order', 'p3_conference', 'user', 'fare', )
        return qs

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            url(r'^stats/data/$', self.admin_site.admin_view(self.stats_data), name='p3-ticket-stats-data'),
        ]
        return my_urls + urls

    def stats_data(self, request):
        from common.jsonify import json_dumps
        from django.db.models import Q
        from collections import defaultdict

        conferences = cmodels.Conference.objects\
            .order_by('conference_start')

        output = {}
        for c in conferences:
            tickets = cmodels.Ticket.objects\
                .filter(fare__conference=c)\
                .filter(Q(orderitem__order___complete=True) | Q(orderitem__order__method__in=('bank', 'admin')))\
                .select_related('fare', 'orderitem__order')
            data = {
                'conference': defaultdict(lambda: 0),
                'partner': defaultdict(lambda: 0),
                'event': defaultdict(lambda: 0),
                'other': defaultdict(lambda: 0),
            }
            for t in tickets:
                tt = t.fare.ticket_type
                date = t.orderitem.order.created.date()
                offset = date - c.conference_start
                data[tt][offset.days] += 1

            for k, v in data.items():
                data[k] = sorted(v.items())


            output[c.code] = {
                'data': data,
            }

        return http.HttpResponse(json_dumps(output), 'text/javascript')


class VotoTalkAdmin(admin.ModelAdmin):
    list_display = ("user", "_name", "talk", "vote")
    list_filter = ("talk__conference",)
    search_fields = [
        "talk__title",
        "user__username",
        "user__last_name",
        "user__first_name",
    ]
    ordering = ("-talk__conference", "talk")

    def _name(self, o):
        url = reverse(
            "profiles:profile", kwargs={"profile_slug": o.user.attendeeprofile.slug}
        )
        return '<a href="%s">%s</a>' % (url, o.user.assopy_user.name())

    _name.allow_tags = True
    _name.admin_order_field = "user__first_name"


class AttendeeProfileAdmin(admin.ModelAdmin):
    list_display = (
        "uuid",
        "slug",
        "_name",
        "_user",
        "company",
        "location",
        "visibility",
    )
    list_filter = ("visibility",)
    search_fields = [
        "user__username",
        "user__last_name",
        "user__first_name",
        "company",
        "location",
    ]

    def _name(self, o):
        url = reverse("profiles:profile", kwargs={"profile_slug": o.slug})
        return '<a href="%s">%s %s</a>' % (
            url,
            o.user.first_name,
            o.user.last_name,
        )

    _name.allow_tags = True
    _name.admin_order_field = "user__first_name"

    def _user(self, o):
        url = reverse("admin:auth_user_change", args=(o.user.id,))
        return '<a href="%s">%s</a>' % (url, o.user.username)

    _user.allow_tags = True
    _user.admin_order_field = "user__username"


class CustomTalkAdminForm(cadmin.MultiLingualForm):

    tags = TagField(
        required=True, widget=LabelWidget(model=cmodels.ConferenceTag)
    )

    class Meta:
        model = cmodels.Talk
        fields = "__all__"


class TalkAdmin(admin.ModelAdmin):
    list_filter = (
        "conference",
        "status",
        "duration",
        "type",
        "level",
        "tags__name",
    )
    list_editable = ("status",)
    search_fields = [
        "title",
        "uuid",
        "talkspeaker__speaker__user__last_name",
        "talkspeaker__speaker__user__first_name",
        "speakers__user__attendeeprofile__company",
    ]

    list_display = (
        "title",
        "uuid",
        "conference",
        "_speakers",
        "_company",
        "duration",
        "status",
        "created",
        "level",
        "domain_level",
        "_tags",
        "_slides",
        "_video",
    )

    prepopulated_fields = {"slug": ("title",)}
    ordering = ("-conference", "title")
    filter_horizontal = ["tags"]
    inlines = [cadmin.TalkSpeakerInlineAdmin]

    form = CustomTalkAdminForm

    def _tags(self, obj):
        return ", ".join(sorted(str(tag) for tag in obj.tags.all()))

    def _speakers(self, obj):
        """Warnings – this is de-optimised version of previous cached query,
        however much easier to work with and much easier to debug"""

        speakers = sorted(
            set(
                (
                    speaker.user.id,
                    speaker.user.assopy_user.name(),
                    speaker.user.email,
                )
                for speaker in obj.speakers.all()
            )
        )

        output = []
        for speaker in speakers:
            args = {
                "url": reverse(
                    "admin:conference_speaker_change", args=[speaker[0]]
                ),
                "name": speaker[1],
                "mail": speaker[2],
            }

            output.append(
                '<a href="%(url)s">%(name)s</a> '
                '(<a href="mailto:%(mail)s">mail</a>)' % args
            )

        return "<br />".join(output)
    _speakers.allow_tags = True

    def _company(self, obj):
        companies = sorted(
            set(
                speaker.user.attendeeprofile.company
                for speaker in obj.speakers.all()
                if speaker.user.attendeeprofile
            )
        )
        return ", ".join(companies)
    _company.admin_order_field = "speakers__user__attendeeprofile__company"

    def _slides(self, obj):
        return bool(obj.slides)
    _slides.boolean = True
    _slides.admin_order_field = "slides"

    def _video(self, obj):
        return bool(obj.video_type) and (
            bool(obj.video_url) or bool(obj.video_file)
        )
    _video.boolean = True
    _video.admin_order_field = "video_type"


admin.site.register(cmodels.Talk, TalkAdmin)


class EventTrackInlineAdmin(admin.TabularInline):
    model = cmodels.EventTrack
    extra = 3

class EventAdmin(admin.ModelAdmin):
    list_display = ('schedule',
                    'start_time',
                    'duration',
                    '_title',
                    '_tracks')
    ordering = ('schedule',
                'start_time',
                'tracks',
                )
    list_filter = ('schedule',
                   'tracks')
    search_fields = ['talk__title',
                     'custom',
                     ]
    inlines = (EventTrackInlineAdmin,
               )

    def _tracks(self, obj):
        return ", ".join([track.track
                          for track in obj.tracks.all()])

    def _title(self, obj):
        if obj.custom:
            return obj.custom
        else:
            return obj.talk

admin.site.register(cmodels.Event, EventAdmin)

class TrackAdmin(admin.ModelAdmin):
    list_display = ('schedule',
                    '_slug',
                    '_date',
                    'track',
                    'title',
                    'order',
                    )
    ordering = ('schedule',
                'order',
                'track',
                )
    list_filter = ('schedule',
                   'schedule__slug',
                   'track',
                   'title')
    list_editable = ('track',
                     'order',
                    )
    search_fields = ['schedule__conference',
                     'schedule__slug',
                     'track',
                     'title',
                     ]
    inlines = (EventTrackInlineAdmin,
               )
    list_select_related = True

    def _slug(self, obj):
        return obj.schedule.slug

    def _date(self, obj):
        return obj.schedule.date

admin.site.register(cmodels.Track, TrackAdmin)

admin.site.unregister(cmodels.Ticket)
admin.site.register(cmodels.Ticket, TicketConferenceAdmin)

admin.site.register(cmodels.VotoTalk, VotoTalkAdmin)
admin.site.register(cmodels.AttendeeProfile, AttendeeProfileAdmin)
