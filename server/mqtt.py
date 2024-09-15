import logging
import paho.mqtt.client as mqtt

from common import config_map, sensor_ids, ingest_queue
from datetime import datetime, timezone

########################################################################
# Humidscope
#
# Humidity/Temperature/Power monitoring system.
#
# by Jim Shortz
#
# MQTT Listener Module
#
# This file contains and automatically starting MQTT listener.
# It receives data readings from the relevant MQTT topics, applies
# timestamps to the data points, and inserts them into ingest_queue.
#
# It was shamelessly stolen from the paho MQTT sample code.
########################################################################

def on_connect(client, userdata, flags, reason_code, properties):
    logging.info(f"MQTT Connected with result code {reason_code}")
    client.subscribe(config_map['mqtt']['topic'])

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        # Record timestamp ASAP
        recvd = datetime.now(timezone.utc).replace(microsecond=0)
        
        sensor_id = sensor_ids.get(msg.topic)
        value = float(msg.payload[:32].decode("utf-8"))

        if sensor_id:
            ingest_queue.put_nowait((recvd, sensor_id, value))
            logging.debug(f'Queued {recvd}, {sensor_id}, {value}')
        else:
            logging.warn(f'Ignoring unknown topic {msg.topic}')
            
    except BaseException as e:
        logging.error(f'Error handling datapoint: {e}')


def start_mqtt():
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    cfg = config_map['mqtt']
    mqttc.username_pw_set(cfg['user'], cfg['pass'])
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message

    mqttc.connect(cfg['host'], cfg['port'], 60)
    mqttc.loop_start()
    logging.info('Started MQTT loop')

start_mqtt()
