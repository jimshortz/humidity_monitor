########################################################################
# MQTT client for web server
#
# This module listens to the raw data on MQTT to more efficiently
# implement the /api/latest endpoint.  It avoids constant DB queries
########################################################################

import logging, os
import paho.mqtt.client as mqtt

from datetime import datetime, timezone

# Global for latest sensor values
latest = {}

# Map topic name to keys in latest
field_names = {
    "basement/indoor_humid": "humidity",
    "basement/indoor_temp": "temperature",
    "basement/power": "power",
}


def on_connect(client, userdata, flags, reason_code, properties):
    global sensor_ids

    logging.info(f"MQTT Connected with result code {reason_code}")

    for topic in field_names.keys():
        logging.debug(f"Subscribing to {topic}")
        client.subscribe(topic)


def on_message(client, userdata, msg):
    global latest

    try:
        payload_str = msg.payload.decode("utf-8").strip(",")
        logging.debug(f"Received {payload_str} on {msg.topic}")

        timestamp = datetime.now(timezone.utc)
        value = float(msg.payload)
        if field_name := field_names.get(msg.topic):
            latest.update(
                {
                    "time": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    field_name: value,
                }
            )
            logging.debug(f"Updated latest to {latest}")
        else:
            logging.warning(f"Ignoring unknown topic {msg.topic}")

    except BaseException as e:
        logging.exception(f"Error handling message {msg}")


mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)


def start_mqtt():
    mqttc.on_connect = on_connect
    mqttc.on_message = on_message

    mqttc.connect(os.environ["MQTT_HOST"], int(os.environ.get("MQTT_PORT", 1883)))
    mqttc.loop_start()
    logging.info("Started MQTT loop")
