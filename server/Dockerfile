# mariadb-python-connect insists on compiling something so
# we must install GCC, musl, and the maria dev library
FROM python:3.12-alpine
COPY requirements.txt requirements.txt
RUN apk add gcc musl-dev mariadb-connector-c-dev && \
pip --no-cache-dir install -r requirements.txt

# Start over and copy just the Python libs from the previous generation.
# We don't need GCC.
FROM python:3.12-alpine
RUN apk add mariadb-connector-c
COPY --from=0 /usr/local/lib/python3.12 /usr/local/lib/python3.12
COPY *.py .
ENV CONFIG_PATH=/config/config.json RUN_ALL=1
VOLUME /config
CMD python3 -u main.py


