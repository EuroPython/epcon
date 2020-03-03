from django.urls import reverse
from django.contrib import admin

from taggit.forms import TagField
from taggit_labels.widgets import LabelWidget

from conference import admin as cadmin
from conference import models as cmodels


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
admin.site.register(cmodels.Talk, TalkAdmin)
admin.site.register(cmodels.Event, EventAdmin)
admin.site.register(cmodels.VotoTalk, VotoTalkAdmin)
admin.site.register(cmodels.AttendeeProfile, AttendeeProfileAdmin)
