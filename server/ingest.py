import logging
import mariadb
import os
import paho.mqtt.client as mqtt
from contextlib import closing
from analysis import analyze
from common import config_map,db_connect

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)

INSERT_SQL = 'insert ignore into raw (sensor_id, value) values (?,?)'

def read_sensor_ids():
    logging.info('Reading sensor ID mappings')
    ret = {}
    with closing(db_connect()) as conn:
        cur = conn.cursor()
        cur.execute("select feed, sensor_id from sensors")
        for (feed, sensor_id) in cur.fetchall():
            ret[feed] = sensor_id
    return ret

# Cache the feed name->sensor id mappings since we do it so much
sensors = read_sensor_ids()

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    logging.info(f"MQTT Connected with result code {reason_code}")
    client.subscribe(config_map['mqtt']['topic'])

# The callback for when a PUBLISH message is received from the server.
conn = None
def on_message(client, userdata, msg):
    global conn
    try:
        logging.debug(f'Handling message {msg.topic} {msg.payload}')

        sensor_id = sensors.get(msg.topic)
        value = msg.payload

        if not sensor_id:
            logging.info(f'Skipping unknown topic {msg.topic}')
        elif len(value) > 32:
            logging.info(f'Skipping malformed message {value[:32]}...')
        else:
            if not conn:
                logging.debug('Attempting to connect to database')
                conn = db_connect()
                logging.info(f'Connected to database')
            cur = conn.cursor()
            cur.execute(INSERT_SQL, (sensor_id, value))
            logging.debug(f'Inserted {sensor_id},{value}')
    except BaseException as e:
        logging.error(f'Error handling datapoint: {e}')
        if conn:
            try:
                logging.debug(f'Closing database connection')
                conn.close()
            except BaseException as e:
                logging.debug(f'Exception closing connection {e}')
            conn = None


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def start_ingest():
    cfg = config_map['mqtt']
    mqttc.username_pw_set(cfg['user'], cfg['pass'])
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message

    mqttc.connect(cfg['host'], cfg['port'], 60)
    mqttc.loop_start()
    logging.info('Started MQTT loop')

def stop_ingest():
    mqttc.loop_stop()
    logging.info('Stopped MQTT loop')
