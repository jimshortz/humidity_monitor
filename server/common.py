import json
import logging
import mariadb
import os

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

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
    return mariadb.Connection(
        host=cfg['host'],
        port=cfg['port'],
        user=cfg['user'],
        password=cfg['pass'],
        database=cfg['database'],
        autocommit=True)
        
# Truncates datetime to beginning of hour
def truncate_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)
