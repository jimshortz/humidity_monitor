import logging
import os
import queue
from common import config_map, ingest_queue, conn, ensure_connected
from schedule import repeat, every

INSERT_SQL = 'INSERT raw (time, sensor_id, value) VALUES (?,?,?) '+ \
    'ON DUPLICATE KEY UPDATE value=value;'    

def read_pending():
    batch = []
    while True:
        try:
            batch.append(ingest_queue.get_nowait())
        except queue.Empty:
            break
    return batch
    
@repeat(every().minute)
def ingest():
    ensure_connected()
    batch = read_pending()
    if batch:
        cur = conn.cursor()
        logging.debug(f'Inserting {batch}')
        cur.executemany(INSERT_SQL, batch)
            
            
