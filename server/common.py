import logging
import mariadb
import os

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

# Configuration
db_host = os.environ.get("DB_HOST", "localhost")
db_port = int(os.environ.get("DB_PORT", "3307"))
db_user = os.environ["DB_USER"]
db_pass = os.environ["DB_PASS"]
db_database = os.environ["DB_DATABASE"]

def create_connection_pool():
    # Create a connection pool to get a cheap auto-reconnect
    # implementation
    pool = mariadb.ConnectionPool(
        host=db_host,
        port=db_port,
        user=db_user,
        database=db_database,
        password=db_pass,
        autocommit=True,
        pool_name="ingest",
        pool_size=1)

    # Return Connection Pool
    return pool

# Truncates datetime to beginning of hour
def truncate_hour(dt):
    return dt.replace(minute=0, second=0, microsecond=0)



db_pool=create_connection_pool()
