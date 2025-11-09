#!env/bin/python

from contextlib import closing
from datetime import date, datetime, timedelta
from flask import Flask, jsonify, request
import calendar
import mysql.connector
import os
import decimal
import logging
from mqtt import latest, start_mqtt

logging.basicConfig(level=logging.INFO)

app = Flask(__name__, static_url_path="")

queries = {
    "hour": """
SELECT DATE_FORMAT(time, '%Y-%m-%dT%H:00:00Z') AS time,
     max(case sensor_id when 1 then avg_value end) as humid,
     max(case sensor_id when 2 then avg_value end) as temp,
     max(case sensor_id when 3 then avg_value end) as power
from hourly
where time between %s and %s
group by time
order by time;
""",
    "day": """
SELECT DATE_FORMAT(time, '%Y-%m-%d') AS time,
     max(case sensor_id when 1 then avg_value end) as humid,
     max(case sensor_id when 2 then avg_value end) as temp,
     max(case sensor_id when 3 then avg_value end) as power
from daily
where time between %s and %s
group by time
order by time;
""",
    "month": """
SELECT DATE_FORMAT(time, '%Y-%m-%d') as m,
            AVG(CASE sensor_id WHEN 1 THEN avg_value END) AS humid,
            AVG(CASE sensor_id WHEN 2 THEN avg_value END) AS temp,
            AVG(CASE sensor_id WHEN 3 THEN avg_value END) AS power
        FROM daily
        WHERE time BETWEEN %s AND %s
        GROUP by YEAR(time), MONTH(time)
        ORDER by 1
        LIMIT 72
""",
    "minute": """
        SELECT DATE_FORMAT(time, '%Y-%m-%d %H:%iZ') AS time,
            AVG(CASE sensor_id WHEN 1 THEN value END) AS humid,
            AVG(CASE sensor_id when 2 THEN value END) AS temp,
            AVG(case sensor_id when 3 THEN value END) AS power
        FROM raw
        WHERE time BETWEEN %s AND %s
        GROUP by 1
        ORDER by 1
        LIMIT 1440
""",
}


# Helper that returns an auto-closing DB connection
def opendb():
    return closing(
        mysql.connector.connect(
            host=os.environ["MARIADB_HOST"],
            port=int(os.getenv("MARIADB_PORT", 3307)),
            user=os.getenv("MARIADB_USER", "humid"),
            password=os.environ["MARIADB_PASSWORD"],
            database=os.getenv("MARIADB_DB_NAME", "humid"),
        )
    )


def parsedate(iso):
    if iso:
        return dateutil.parser.parse(iso)
    return None


@app.route("/")
def root():
    return app.send_static_file("index.html")


@app.route("/api/v1.0/latest", methods=["GET"])
def get_latest():
    # Return latest values from MQTT topic
    return jsonify(latest)


@app.route("/api/v1.0/measurements", methods=["GET"])
def get_measurements():
    now = datetime.utcnow()
    end = now
    start = end - timedelta(days=1)
    if "start" in request.args:
        start = datetime.fromisoformat(request.args["start"])
    if "end" in request.args:
        end = datetime.fromisoformat(request.args["end"])
    rollup = request.args.get("rollup") or "hour"
    if rollup == "month":
        # Snap dates to month boundaries
        start = start.date().replace(day=1)
        _, days_in_month = calendar.monthrange(end.year, end.month)
        end = end.date().replace(day=1) + timedelta(days_in_month)
    elif rollup == "day":
        # Not really necessary but for consistency
        start = start.date()
        end = end.date()

    with opendb() as db:
        cursor = db.cursor()
        print(f"Executing {queries[rollup]}, {start}, {end}")
        cursor.execute(queries[rollup], (start, end))
        rows = [[row[0], float(row[1]), float(row[2]), float(row[3])] for row in cursor]
        return jsonify(rows)


@app.route("/api/v1.0/alarms", methods=["GET"])
def get_alarms():
    sql = "SELECT * FROM alarms;"
    with opendb() as db:
        cursor = db.cursor(dictionary=True)
        cursor.execute(sql)
        return jsonify(cursor.fetchall())

# Start the MQTT listener in the background
with app.app_context():
    start_mqtt()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)
