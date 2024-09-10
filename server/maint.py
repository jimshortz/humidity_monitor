#!/usr/local/bin/python3 -u

import logging
from datetime import datetime, timedelta, timezone
from common import conn, truncate_hour
from schedule import repeat, every

# Constants
max_gap = timedelta(minutes=2)
comp_threshold = 200

@repeat(every().hour.at(':02'))
def cycle_analyze():
    cur = conn.cursor()

    # Find last completed cycle
    cur.execute("select max(end_time) from cycles")
    start = cur.fetchone()[0] or datetime(2000,1,1,0,0,0)

    (was_on, was_time) = (False, start)
    (on_time, off_time) = (None, None)

    logging.info(f"Detecting cycles since {start}")
    cur.execute("select time, value from raw where sensor_id = ? and time >= ?", (3, start))
    row_count = 0
    for (is_time, power) in cur.fetchall():
        is_on = power >= comp_threshold   # Current state of compressor

        if (is_time - was_time) > max_gap:
            logging.warning("Data gap between %s and %s.  Discarding cycles.", was_time, is_time)
            (on_time, off_time) = (None, None)
            was_on = True   # Don't start next cycle until off->on observed

        if not was_on and is_on:
            logging.debug("Turned on at %s", is_time)
            if on_time and off_time:
                cycle = (on_time, off_time, is_time)
                logging.debug("Inserting cycle %s", cycle)
                row_count = row_count + 1
                cur.execute("insert into cycles (start_time, off_time, end_time) values (?,?,?)", cycle)
            (on_time, off_time) = (is_time, None)
        elif was_on and not is_on:
            logging.debug("Turned off at %s", is_time)
            off_time = is_time

        # Save state for next reading
        (was_time, was_on) = (is_time, is_on)

    logging.info(f'Wrote {row_count} records')

@repeat(every().hour.at(':02'))
def hourly_summary():
    cur = conn.cursor()
    cur.execute("select max(time) from hourly")
    start = cur.fetchone()[0] or datetime.min
    start = start + timedelta(hours=1)
    end = truncate_hour(datetime.now(timezone.utc))
    logging.info("Generating hourly records between %s and %s", start, end)
    cur.execute("""
    insert  into hourly (time, sensor_id, samples, min_value, avg_value, max_value)
    select  timestamp(date(time), maketime(hour(time), 0, 0)),
            sensor_id,
            count(*),
            min(value),
            avg(value),
            max(value)
    from    raw
    where   time >= ? and time < ?
    group by 1, 2""", (start, end))
    logging.info(f'Wrote {cur.rowcount} records')

@repeat(every().day.at('00:15'))
def daily_summary():
    cur = conn.cursor()
    cur.execute("select max(time) from daily")
    start = cur.fetchone()[0] or datetime.min.date()
    start = start + timedelta(days=1)
    end = datetime.now(timezone.utc).date()
    logging.info("Generating daily records between %s and %s", start, end)
    cur.execute("""
    insert  into daily (time, sensor_id, samples, min_value, avg_value, max_value)
    select  date(time),
            sensor_id,
            count(*),
            min(value),
            avg(value),
            max(value)
    from    raw
    where   time >= ? and time < ?
    group by 1, 2""", (start, end))
    logging.info("Wrote %s rows", cur.rowcount)

