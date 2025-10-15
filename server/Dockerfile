FROM python:3.12-alpine
COPY requirements.txt requirements.txt
COPY *.py .
ENV CONFIG_PATH=/config/config.json RUN_ALL=1
VOLUME /config
CMD python3 -u main.py


