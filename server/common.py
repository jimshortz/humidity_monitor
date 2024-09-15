########################################################################
# Humidscope
#
# Humidity/Temperature/Power monitoring system.
#
# by Jim Shortz
#
# Common module
#
# This file contains globals (initialized at startup) and utility
# methods needed by the other modules.
#
# Note - A module can be tested in isolation by simply loading it
# with python -i and calling the appropriate job/function under test.
########################################################################

import json
import logging
import mariadb
import os
import queue
from contextlib import closing

# Allows log level to be overriden by a environment variable.
LOG_LEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()

# Initialize the logger
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=LOG_LEVEL)

# Loads the config.json map
def _load_config():
    path = os.environ.get("CONFIG_PATH")
    if not path:
        raise RuntimeError("Must set CONFIG_PATH environment variable")
    with open(path, 'r') as f:
        return json.load(f)
    
# Creates a connection to MariaDB
# Should probably retry but it doesn't
def _db_connect():
    cfg = config_map['mariadb']
    conn = mariadb.Connection(
        host=cfg['host'],
        port=cfg['port'],
        user=cfg['user'],
        password=cfg['pass'],
        database=cfg['database'],
        autocommit=True)
    logging.info(f'Connected to database')
    return conn

# Used to build the sensor_ids() map
SENSOR_SQL = 'SELECT feed, sensor_id FROM sensors'
def _read_sensor_ids():
    global conn
    logging.info('Reading sensor ID mappings')
    with closing(conn.cursor()) as cur:
        cur.execute(SENSOR_SQL)
        return {feed: sensor_id for (feed, sensor_id) in cur.fetchall()}

# Tests the connection and reconnects as necessary
# Despite the name, doesn't retry if reconnect
# fails.
def ensure_connected():
    try:
        with closing(conn.cursor()) as cur:
            cur.execute('SELECT VERSION()')
    except mariadb.Error:
        conn.reconnect()
        logging.info(f'Reconnected to database')
        
# Truncates a datetime to the beginning of hour
def truncate_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)

# Globals
config_map = _load_config()
conn = _db_connect()
sensor_ids = _read_sensor_ids()
mail_queue = []
ingest_queue = queue.Queue()
