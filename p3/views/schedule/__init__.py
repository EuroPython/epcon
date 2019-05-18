from datetime import timedelta

from conference.models import Event, Schedule
from conference.utils import TimeTable2
from django.shortcuts import render

from .grid import Grid, GridTime, ScheduleGrid, Talk


def _get_time_indexes(start_time, end_time, times):
    for index, time in enumerate(times):
        end_time_index = index

        if time > end_time:
            break

    start = times.index(start_time) + 1
    end = end_time_index

    return start, end


def _build_timetable(schedule):
    return


def schedule(request, conference):
    # TODO: filter by day
    sids = Schedule.objects.filter(conference=conference).values_list(
        "id", flat=True
    )

    from conference.dataaccess import schedules_data

    schedule_data = schedules_data(sids)[0]
    timetable = TimeTable2.fromSchedule(schedule_data["id"])

    starred_talks_ids = []

    if request.user.is_authenticated():
        starred_talks_ids = (
            Event.objects.filter(
                eventinterest__user=request.user, eventinterest__interest__gt=0
            )
            .filter(schedule__conference=conference)
            .values_list("id", flat=True)
        )

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

    ctx = {"conference": conference, "schedule": schedule}

    return render(request, "ep19/bs/schedule/schedule.html", ctx)
