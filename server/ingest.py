########################################################################
# Humidscope
#
# Humidity/Temperature/Power monitoring system.
#
# by Jim Shortz
#
# Data Ingest Module
#
# This file contains a scheduled job that reads data points from the
# ingest_queue and writes them to the database.  It runs once per minute
# for low(ish) latency and reliability.
########################################################################

import logging
import os
import queue
from common import config_map, ingest_queue, conn, DataPoint
from contextlib import closing
from schedule import repeat, every
from math import isnan

INSERT_SQL = 'INSERT raw (time, sensor_id, value) VALUES (%s,%s,%s) '+ \
    'ON DUPLICATE KEY UPDATE value=value;'    

def read_pending():
    batch = []
    while True:
        try:
            data = ingest_queue.get_nowait()
            if isnan(data.value):
                logging.warn(f'Discarding {data}')
            else:
                batch.append((data.time, data.sensor_id, data.value))
        except queue.Empty:
            break
    return batch

@repeat(every().minute)
def ingest():
    batch = read_pending()
    if batch:
        count = len(batch)
        with closing(conn.cursor()) as cur:
            start = time.monotonic()
            cur.executemany(INSERT_SQL, batch)
            elapsed = time.monotonic() - start
            logging.info(f'Inserted {len(batch)} data points in {elapsed:0.3f}s {elapsed/count:0.3}s/rec')
            
            
