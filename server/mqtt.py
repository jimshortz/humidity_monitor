import logging
import paho.mqtt.client as mqtt

from common import config_map, sensor_ids, ingest_queue, DataPoint
from datetime import datetime, timezone
from decimal import *

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
        datapoint = DataPoint(datetime.now(timezone.utc).replace(microsecond=0),
                              sensor_ids.get(msg.topic),
                              Decimal(msg.payload.decode("utf-8")))

        if datapoint.sensor_id is None:
            logging.warning(f'Ignoring unknown topic {msg.topic}')
            return
            
        try:
            ingest_queue.put_nowait(datapoint)
            logging.debug(f'Queued {datapoint}')
        except queue.Full:
            logging.warning(f'Queue is full, discarding {datapoint}')
            return
            
    except BaseException as e:
        logging.exception(f'Error handling message {msg}')


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
