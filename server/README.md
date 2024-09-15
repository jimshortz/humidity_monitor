# Data logging/analysis support

This directory contains a Dockerized python application for collecting
and analyzing humidity, temperature, and power data.  It runs as a daemon, listening to MQTT topics and writing data to the DB as received.  It also kicks off an hourly job that:
* Summarizes hourly statistics into the hourly table
* Summarizes daily statistics into the daily table
* Produces cycle data indicating how long the dehumidifer spent on and off
* Prunes old raw data

# Configuration

All settings live in the `config.json` file.  The location of this file is
passed as a single environment variable `CONFIG_PATH`.  In a local environment
this can be whatever.  In a container, the config file should be mounted
read only into the /config directory.

See `config.json.sample` for a template you can use.

# Testing locally (without Docker)
```
python3 -m venv venv
source venv/bin/activate
pip -r requirements.txt
CONFIG_PATH=./config.json python main.py
```

# Building
```
docker build --platform linux/amd64 -t humid .
```

# Testing locally (in Docker)
Assuming desired config file is in the local directory as `config.json.dev`:
```
docker run -v .:/config -e CONFIG_PATH=/config/config.json.dev humid
```

# Loading Adafruit Data

If you screw up your local ingest, you can download data from Adafruit
using their "Download All Data" button on the feeds page.  It will
produce a CSV that can be loaded with:

```
CREATE TABLE `ada_raw` (
  `time` datetime NOT NULL,
  `sensor_id` int(11) NOT NULL,
  `value` decimal(6,2) NOT NULL,
  PRIMARY KEY (`time`, `sensor_id`));
  
LOAD DATA LOCAL INFILE 'indoor_humid-20240828-1445.csv'
IGNORE
INTO TABLE ada_raw
FIELDS TERMINATED BY ','
IGNORE 1 LINES
(@dummy,value,@dummy,time,@dummy,@dummy,@dummy)
SET sensor_id=1;
```

The last statement should be customized for the filename and sensor ID
being loaded.  Repeat the LOAD DATA` statements for every file.  Using
the `ada_raw` table allows you to preview what is going to be loaded,
trim it up, etc.  Once you are ready to import it, use:

```
INSERT INTO raw
SELECT * FROM ada_raw
ON DUPLICATE KEY UPDATE raw.value=raw.value;

DROP TABLE ada_raw
```
