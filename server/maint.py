#!/usr/local/bin/python3 -u

########################################################################
# Humidscope
#
# Humidity/Temperature/Power monitoring system.
#
# by Jim Shortz
#
# DB Maintenance module
#
# This file contains scheduled jobs that perform maintenance on the DB
# and calculate additional summaries of the data.
########################################################################

import logging
from datetime import datetime, timedelta, timezone
from common import conn, truncate_hour, config_map
from contextlib import closing
from schedule import repeat, every

# Constants
max_gap = timedelta(minutes=2)
comp_threshold = 200

INSERT_CYCLE_SQL = 'insert into cycles (start_time, on_duration, off_duration) values (?,?,?)'
LAST_CYCLE_SQL = '''select date_add(start_time, interval on_duration+off_duration second)
from cycles order by start_time desc limit 1;'''

@repeat(every().hour.at(':02'))
def cycle_analyze():
    with closing(conn.cursor()) as cur:
        
        # Find last completed cycle
        cur.execute(LAST_CYCLE_SQL)
        row = cur.fetchone()
        if row:
            start = row[0]
        else:
            start = datetime(2000,1,1,0,0,0)

        (was_on, was_time) = (False, start)
        (on_time, off_time) = (None, None)

        logging.info(f"Detecting cycles since {start}")
        cur.execute("select time, value from raw where sensor_id = ? and time >= ?", (3, start))
        row_count = 0
        batch = []
        for (is_time, power) in cur.fetchall():
            is_on = power >= comp_threshold   # Current state of compressor

            if (is_time - was_time) > max_gap:
                logging.warning("Data gap between %s and %s.  Discarding cycles.", was_time, is_time)
                (on_time, off_time) = (None, None)
                was_on = True   # Don't start next cycle until off->on observed

            if not was_on and is_on:
                logging.debug("Turned on at %s", is_time)
                if on_time and off_time:
                    cycle = (on_time, (off_time-on_time).total_seconds(), (is_time - off_time).total_seconds())
                    logging.debug(f'Inserting cycle {cycle[0].isoformat()},{cycle[1]},{cycle[2]}')
                    batch.append(cycle)
                    if len(batch) > 500:
                        cur.executemany(INSERT_CYCLE_SQL, batch)
                        row_count = row_count + len(batch)
                        batch.clear()
                (on_time, off_time) = (is_time, None)
            elif was_on and not is_on:
                logging.debug("Turned off at %s", is_time)
                off_time = is_time

            # Save state for next reading
            (was_time, was_on) = (is_time, is_on)

        if batch:
            cur.executemany(INSERT_CYCLE_SQL, batch)
            row_count = row_count + len(batch)
        
    logging.info(f'Wrote {row_count} records')

@repeat(every().hour.at(':02'))
def hourly_summary():
    with closing(conn.cursor()) as cur:
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
    with closing(conn.cursor()) as cur:
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

@repeat(every().day.at('06:00'))
def prune_raw():
    days_to_keep = config_map['retention']['raw']
    oldest = datetime.now(timezone.utc).date() - timedelta(days=days_to_keep)
    logging.info(f'Pruning raw records older than {oldest.isoformat()}')
    total_rows = 0
    with closing(conn.cursor()) as cur:
        while True:
            cur.execute('DELETE FROM raw WHERE time < ? LIMIT 5000', (oldest,))
            total_rows = total_rows + cur.rowcount
            if cur.rowcount < 5000:
                break
    logging.info(f'Pruned {total_rows} records')
