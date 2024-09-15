FROM python:3.12-alpine
COPY requirements.txt requirements.txt
RUN pip --no-cache-dir install -r requirements.txt
COPY *.py .
ENV CONFIG_PATH=/config/config.json
ENV DATA_PATH=/data
VOLUME /config
VOLUME /data
CMD python3 -u ingest.py


