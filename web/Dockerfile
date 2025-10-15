FROM python:3.12-alpine
COPY requirements.txt requirements.txt
RUN pip --no-cache-dir install -r requirements.txt
COPY *.py /
COPY static static
EXPOSE 5000 5000
# No, we're not running a proper web server, but this is a home app
CMD flask run --no-debug --host 0.0.0.0


