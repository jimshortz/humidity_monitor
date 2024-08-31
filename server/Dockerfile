FROM python:3.12-alpine
COPY requirements.txt requirements.txt
RUN <<EOF
apk add gcc musl-dev mariadb-connector-c-dev
pip --no-cache-dir install -r requirements.txt
EOF
COPY *.py .
CMD python3 -u main.py


