# Super Simple Logger

This directory contains a Dockerized python application for collecting
data from the humidity/temperature/power sensor.  It listens to MQTT
topics defined in the config file and writes to the raw_dir location
specified there.

While short on features, this has been super-reliable.  All it needs
is a directory to write to and MQTT connectivity.  No database, email,
or any other nonsense.

## Configuration

All settings live in the `config.json` file.  The location of this file is
passed as a single environment variable `CONFIG_PATH`.  In a local environment
this can be whatever.  In a container, the config file should be mounted
read only into the /config directory.

See `config.json.sample` for a template you can use.

## Testing locally (without Docker)
```
python3 -m venv venv
source venv/bin/activate
pip -r requirements.txt
CONFIG_PATH=./config.json python main.py
```

## Building
```
docker build --platform linux/amd64 -t humid-simple .
```

## Testing locally (in Docker)
Assuming desired config file is in the local directory as `config.json.dev`:
```
docker run -v .:/config -e CONFIG_PATH=/config/config.json.dev humid-simple
```
