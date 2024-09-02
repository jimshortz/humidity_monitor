import logging
from analysis import analyze
from ingest import start_ingest, stop_ingest
from time import sleep
from datetime import datetime, timedelta, timezone

def next_run():
    now = datetime.now(timezone.utc)
    t = now.replace(minute=2,second=0,microsecond=0)
    if t < now:
        t = t + timedelta(hours=1)
    return t

def sleep_until(t):
    d = t - datetime.now(timezone.utc)
    if d.total_seconds() > 0:
        logging.debug(f'Snoozing {d}')
        sleep(d.total_seconds())

# Main
logging.info('Starting')

start_ingest()

while True:
    try:
        analyze()
    except BaseException as e:
        logging.error(f'Analyze job got exception {e}')

    wakeup = next_run()
    logging.info(f'Next run at {wakeup}')
    sleep_until(wakeup)

logging.info('Exiting')

