#
# CSS for the conference schedule
#

# Start times
START_TIMES = [x for x in range(800, 2205, 5) if x % 100 < 60]

# Durations
DURATIONS = [x for x in range(5, 645, 5)]

###

def write_time_css(class_name, start_times, css_top_offset, css_top_increment):
    top = css_top_offset
    for time in start_times:
        print('%s .time-%04i { top: %ipx; }' %
              (class_name, time, top))
        print('%s .offset-%04i { margin-top: %ipx; }' %
              (class_name, time, -top))
        top += css_top_increment

def write_duration_css(class_name, durations, css_height_offset, css_height_scale):
    for duration in durations:
        height = int(css_height_offset + duration * css_height_scale)
        print('%s .duration-%i { height: %ipx; padding-top: 0px; }' %
              (class_name, duration, height))

###

def main():        
    write_duration_css('.conference-schedules.timetable.vertical-narrow', DURATIONS,
                       css_height_offset=0, css_height_scale=2.0)
    write_time_css('.conference-schedules.timetable.vertical-narrow', START_TIMES,
                   css_top_offset=40, css_top_increment=10)
    print ('')
    write_duration_css('.conference-schedules.timetable.vertical', DURATIONS,
                       css_height_offset=0, css_height_scale=4.0)
    write_time_css('.conference-schedules.timetable.vertical', START_TIMES,
                   css_top_offset=40, css_top_increment=20)


if __name__ == '__main__':
    main()
