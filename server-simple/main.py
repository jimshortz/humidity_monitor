########################################################################
# Humidscope
#
# Humidity/Temperature/Power monitoring system.
#
# by Jim Shortz
#
# Super simple file logger
#
# This program will read datapoints from MQTT, timestamp them, and
# write them into a CSV file.  The format of the file is suitable for
# loading into the MariaDB raw table.
#
# It creates a new file per day.  That's it.
########################################################################

import logging
import os
import paho.mqtt.client as mqtt
from common import config_map
from datetime import date, datetime, timezone

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s', level=logging.INFO)

def load_config():
    path = os.environ.get("CONFIG_PATH")
    if not path:
        raise RuntimeError("Must set CONFIG_PATH environment variable")
    with open(path, 'r') as f:
        return json.load(f)
    
config_map = load_config()

# Maps topic names to sensor_id values
sensor_ids = config_map['sensor_ids']

# Day of last timestamp written
last_day = None

# Current file handle
file = None

# Creates or appends to the appropriate file for the given day
def open_file(day):
    fn = os.path.join(config_map['raw_dir'], f'{day.isoformat()}.csv')
    fh = open(fn, 'at', buffering=1)
    if fh.tell() == 0:
        logging.info(f'Creating file {fn}')
        fh.write('sensor_id,time,value\n')
    else:
        logging.info(f'Appending to file {fn}')
    return fh

# Writes datapoint to CSV file
def write_data(time, sensor_id, value):
    global file, last_day
    
    day = time.date()
    if day != last_day:
        if file:
            file.close()
            file = None
            last_day = day
        file = open_file(day)
        last_day = day
    file.write(f'{time.isoformat()},{sensor_id},{value:.2f}\n')

# The callback for when the client receives a CONNACK response from the server.
def on_connect(client, userdata, flags, reason_code, properties):
    logging.info(f"MQTT Connected with result code {reason_code}")
    client.subscribe(config_map['mqtt']['topic'])

# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    try:
        global last_day,file
        
        recvd = datetime.now(timezone.utc).replace(microsecond=0)
        sensor_id = sensor_ids.get(msg.topic)
        value = float(msg.payload[:32].decode("utf-8"))

        if sensor_id:
            write_data(recvd, sensor_id, value)
        else:
            logging.warn(f'Ignoring unknown topic {msg.topic}')
            
    except BaseException as e:
        logging.error(f'Error handling datapoint: {e}')

mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)


cfg = config_map['mqtt']
mqttc.username_pw_set(cfg['user'], cfg['pass'])
mqttc.on_connect = on_connect
mqttc.on_message = on_message

mqttc.connect(cfg['host'], cfg['port'], 60)
logging.info('Started MQTT loop')
mqttc.loop_forever()
