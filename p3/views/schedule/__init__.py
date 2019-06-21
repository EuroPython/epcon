from datetime import timedelta, date

from django import http
from django.shortcuts import render, get_object_or_404

from conference.models import Conference, Schedule
from conference.utils import TimeTable2

from .grid import Grid, GridTime, ScheduleGrid, Talk


def _get_time_indexes(start_time, end_time, times):
    for index, time in enumerate(times):
        end_time_index = index

        if time > end_time:
            break

    start = times.index(start_time) + 1
    end = end_time_index

    return start, end


def schedule(request, conference, day=None, month=None):
    from conference.dataaccess import schedules_data

    selected_slug = request.GET.get('selected', None)

    months = [
        "january",
        "february",
        "march",
        "april",
        "may",
        "june",
        "july",
        "august",
        "september",
        "october",
        "november",
        "december",
    ]

    # TODO: filter by day
    schedules = Schedule.objects.filter(conference=conference).values(
        "id", "date"
    )

    days = [schedule["date"] for schedule in schedules]
    if not days:
        raise http.Http404()

    # Handle the case of day or month being not provided - use the
    # first day of the conference
    if not month or not day:
        first_day = min(days)
        month_index = first_day.month
        day = first_day.day
    else:
        try:
            month_index = months.index(month) + 1
        except:
            raise http.Http404()

    print(day, month, month_index)

    selected_date = date(days[0].year, month_index, int(day))
    current_schedule = next(
        (
            schedule
            for schedule in schedules
            if schedule["date"] == selected_date
        ),
        None,
    )

    if current_schedule is None:
        raise http.Http404()

    schedule_data = schedules_data([current_schedule["id"]])[0]
    timetable = TimeTable2.fromSchedule(schedule_data["id"])

    # Not implemented
    starred_talks_ids = []
    #
    # if request.user.is_authenticated():
    #     starred_talks_ids = (
    #         Event.objects.filter(
    #             eventinterest__user=request.user, eventinterest__interest__gt=0
    #         )
    #         .filter(schedule__conference=conference)
    #         .values_list("id", flat=True)
    #     )

    times = []
    tracks = timetable._tracks
    talks = []

    all_times = set()

    for time, talks_for_time in timetable.iterOnTimes():
        times.append(time)
        all_times.add(time)

        for talk in talks_for_time:
            all_times.add(talk["end_time"])

    all_times = sorted(list(all_times))

    new_times = []
    start = all_times[0]
    end = all_times[-1]

    while start <= end:
        new_times.append(start)
        start += timedelta(minutes=5)

    all_times = new_times

    seen = set()

    for time, talks_for_time in timetable.iterOnTimes():
        for talk in talks_for_time:
            if talk["id"] in seen:
                continue

            seen.add(talk["id"])

            start_row, end_row = _get_time_indexes(
                talk["time"], talk["end_time"], all_times
            )

            talk_meta = talk.get("talk", {}) or {}

            t = Talk(
                title=talk.get("custom", "") or talk.get("name", ""),
                id=talk["id"],
                starred=talk["id"] in starred_talks_ids,
                selected=selected_slug and selected_slug == talk_meta.get("slug", None),
                tracks=talk["tracks"],
                start=time,
                end=talk["end_time"],
                start_column=tracks.index(talk["tracks"][0]) + 1,
                end_column=tracks.index(talk["tracks"][-1]) + 2,
                start_row=start_row,
                end_row=end_row,
                slug=talk_meta.get("slug", None),
                language=talk_meta.get("language", None),
                level=talk_meta.get("level", None),
                speakers=talk_meta.get("speakers", []),
                can_be_starred=talk_meta.get("id", 0) > 0,
            )

            talks.append(t)

    grid_times = []

    for index, time in enumerate(times[:-1]):
        next_time = times[index + 1]

        start_row, end_row = _get_time_indexes(time, next_time, all_times)

        grid_times.append(
            GridTime(time=time, start_row=start_row, end_row=end_row)
        )

    grid_times.append(
        GridTime(time=times[-1], start_row=end_row, end_row=len(all_times))
    )

    schedule = ScheduleGrid(
        day=schedule_data["date"],
        tracks=tracks,
        talks=talks,
        grid=Grid(times=grid_times, rows=len(all_times), cols=len(tracks)),
    )

    ctx = {"conference": conference, "schedule": schedule, "days": days}

    return render(request, "ep19/bs/schedule/schedule.html", ctx)
