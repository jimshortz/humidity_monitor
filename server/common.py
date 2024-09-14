import json
import logging
import mariadb
import os
import queue

LOG_LEVEL = os.environ.get('LOGLEVEL', 'INFO').upper()
logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=LOG_LEVEL)

def load_config():
    path = os.environ.get("CONFIG_PATH")
    if not path:
        raise RuntimeError("Must set CONFIG_PATH environment variable")
    with open(path, 'r') as f:
        return json.load(f)
    
config_map = load_config()

# Creates a connection to MariaDB
def db_connect():
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

def ensure_connected():
    try:
        cur = conn.cursor()
        cur.execute('SELECT VERSION()')
    except mariadb.Error:
        conn.reconnect()
        logging.info(f'Reconnected to database')
        
# Truncates datetime to beginning of hour
def truncate_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)

SENSOR_SQL = 'SELECT feed, sensor_id FROM sensors'
def read_sensor_ids():
    global conn
    logging.info('Reading sensor ID mappings')
    cur = conn.cursor()
    cur.execute(SENSOR_SQL)
    return {feed: sensor_id for (feed, sensor_id) in cur.fetchall()}

# Globals
conn = db_connect()
mail_queue = []
ingest_queue = queue.Queue()
sensor_ids = read_sensor_ids()
