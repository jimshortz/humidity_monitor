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

INSERT_SQL = 'INSERT raw (time, sensor_id, value) VALUES (?,?,?) '+ \
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
        with closing(conn.cursor()) as cur:
            logging.debug(f'Inserting {batch}')
            cur.executemany(INSERT_SQL, batch)
    logging.debug(f'Inserted {len(batch)} data points')
            
            
