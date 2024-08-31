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

def create_connection_pool():
    # Create a connection pool to get a cheap auto-reconnect
    # implementation
    cfg = config_map['mariadb']
    pool = mariadb.ConnectionPool(
        host=cfg['host'],
        port=cfg['port'],
        user=cfg['user'],
        password=cfg['pass'],
        database=cfg['database'],
        autocommit=True,
        pool_name="ingest",
        pool_size=1)

    # Return Connection Pool
    return pool

# Truncates datetime to beginning of hour
def truncate_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)



db_pool=create_connection_pool()
