#! venv/bin/python -u

########################################################################
# Humidscope
#
# Humidity/Temperature/Power monitoring system.
#
# by Jim Shortz
#
# Main module.
#
# This is the entry point for the system.  It simply loads the
# constituent models and services the scheduler.
########################################################################

import logging
import os
import schedule

from common import ensure_connected
from datetime import datetime, timedelta, timezone
from time import sleep

# Order matters here.  We want MQTT to start immediately and the
# others to run in this order in the scheduler
import mqtt
import ingest
import alarm
import mail
import maint

if os.environ.get('RUN_ALL'):
    logging.info('Running all jobs')
    schedule.run_all()
    
# Main loop.  Processes the schedule and makes sure the DB is
# alive before starting a job.
logging.info('Starting scheduler')
while True:
    snooze = 0
    try:
        ensure_connected()
        schedule.run_pending()
        snooze = schedule.idle_seconds()
    except BaseException as e:
        logging.exception(f'Exception in job')
        snooze = 60
        
    if snooze > 0:
        sleep(snooze)


