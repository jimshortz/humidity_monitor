# Super Simple Logger

In the spirit of keeping simple things simple, here is a logger that simply
writes a CSV file.  It is written in C and has no dependencies other than
the mosquitto libraries.

While short on features, this has been super-reliable.  All it needs
is a directory to write to and MQTT connectivity.  No database, email,
or any other nonsense.

## Configuration

The `MQTT_HOST` and `MQTT_PORT` environment variables can be set as
expected.  `MQTT_TOPIC` may also be set to customize which topic is
subscribed to.  Use the # wildcard for multiple.

`/data` should be mounted to an external persistent volume.  It must
contain a `raw/` subdirectory writable by the container.

## Building
```
docker build --platform linux/amd64 -t humid-simple .
```

## Testing locally (in Docker)
Assuming desired config file is in the local directory as `config.json.dev`:
```
docker run -e MQTT_HOST=yourhost -v ./data:/data humid-simple
```
