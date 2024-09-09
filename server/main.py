import logging
import schedule

from datetime import datetime, timedelta, timezone
from time import sleep

# Order matters here.  We want MQTT to start immediately and the
# others to run in this order in the scheduler
import mqtt
import ingest
import alarm
import mail
import maint

# Main
logging.info('Starting scheduler')
while True:
    snooze = 0
    try:
        schedule.run_pending()
        snooze = schedule.idle_seconds()
    except BaseException as e:
        logging.exception(f'Exception in job')
        snooze = 60
        
    if snooze > 0:
        sleep(snooze)


