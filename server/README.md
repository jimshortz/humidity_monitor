# Data logging/analysis support

This directory contains a Dockerized python application for collecting
and analyzing humidity, temperature, and power data.  It runs as a daemon, listening to MQTT topics and writing data to the DB as received.  It also kicks off an hourly job that:
* Summarizes hourly statistics into the hourly table
* Summarizes daily statistics into the daily table
* Produces cycle data indicating how long the dehumidifer spent on and off
* Prunes old raw data (TODO)

# Configruration

TODO - Explain env vars

# Building

docker build --platform linux/amd64 -t humid .

# Testing locally (without Docker)
Create runit.sh file to include env vars.  Include
```
python3 main.py
```
at the end.

```
python3 -m venv venv
source venv/bin/activate
pip -r requirements.txt
./runit.sh
```

# Testing locally (in Docker)
Write `env` file with appropriate variables

```
docker run --env-file env humid
```
