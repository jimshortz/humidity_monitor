import logging
import mariadb
import os
import paho.mqtt.client as mqtt
from contextlib import closing
from analysis import analyze
from common import db_pool

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.DEBUG)

# Configuration
mqtt_host = os.environ.get("MQTT_HOST", "localhost")
mqtt_port = int(os.environ.get("MQTT_PORT", 1883))
mqtt_user = os.environ.get("MQTT_USER")
mqtt_pass = os.environ.get("MQTT_PASS")
mqtt_topic = os.environ.get("MQTT_TOPIC")

INSERT_SQL = 'insert ignore into raw (sensor_id, value) values (?,?)'

# TODO - Read from DB
sensors = {
    'basement/indoor_humid': 1,
    'basement/indoor_temp': 2,
    'basement/power' : 3}


# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    logging.info(f"MQTT Connected with result code {reason_code}")
    client.subscribe(mqtt_topic)

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        logging.debug(f'Handling message {msg.topic} {msg.payload}')

        sensor_id = sensors.get(msg.topic)
        value = msg.payload

        if not sensor_id:
            logging.info(f'Skipping unknown topic {msg.topic}')
        elif len(value) > 32:
            logging.info(f'Skipping malformed message {value[:32]}...')
        else:
            with closing(db_pool.get_connection()) as conn:
                cur = conn.cursor()
                cur.execute(INSERT_SQL, (sensor_id, value))
                logging.debug(f'Inserted {sensor_id},{value}')
    except BaseException as e:
        logging.error(f'Error handling datapoint: {e}')


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

def start_ingest():
    mqttc.username_pw_set(mqtt_user, mqtt_pass)
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message

    mqttc.connect(mqtt_host,mqtt_port, 60)
    mqttc.loop_start()
    logging.info('Started MQTT loop')

def stop_ingest():
    mqttc.loop_stop()
    logging.info('Stopped MQTT loop')
