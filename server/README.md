# Data logging/analysis support

This directory contains a Dockerized python application for collecting
and analyzing humidity, temperature, and power data.  It runs as a daemon, listening to MQTT topics and writing data to the DB as received.  It also kicks off an hourly job that:
* Summarizes hourly statistics into the hourly table
* Summarizes daily statistics into the daily table
* Produces cycle data indicating how long the dehumidifer spent on and off
* Prunes old raw data (TODO)

# Configuration

All settings live in the `config.json` file.  The location of this file is
passed as a single environment variable `CONFIG_PATH`.  In a local environment
this can be whatever.  In a container, the config file should be mounted
read only into the /config directory.

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
