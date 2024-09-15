########################################################################
# Humidscope
#
# Humidity/Temperature/Power monitoring system.
#
# by Jim Shortz
#
# Alarming Module
#
# This file contains a scheduled job that evaluates recent data
# and fires alarms if things cross into or out of erronous zones.
#
# The alarm definitions and states are maintained in the database.
# Outgoing email messages are placed into mail_queue for delivery
# by the SMTP module.
#
# This should be scheduled after ingest so it is alarming on up-to-date
# data.
########################################################################

import logging
from common import conn, config_map, mail_queue, topics_by_id
from contextlib import closing
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from enum import Enum
from schedule import every, repeat

AlarmState = Enum('AlarmState', ['UNKNOWN','STARTUP', 'TOO_LOW','TOO_HIGH','HEALTHY'])

Aggregate = Enum('Aggregate', ['COUNT','AVG', 'MIN', 'MAX'])
email_sender = config_map['email']['sender']
email_recipients = config_map['email']['recipients']

@dataclass
class AlarmDefinition:
    id:str
    agg: Aggregate
    window:timedelta
    message:str
    sensor_id:int | None = None
    min:float | None = None
    max:float | None = None

LOAD_ALARM_SQL = 'SELECT id, sensor_id, aggregate, window, min_value, max_value, message, state '\
    'FROM alarms'

def load_alarms() -> tuple[list[AlarmDefinition], dict[str, AlarmState]]:
    with closing(conn.cursor()) as cur:
        cur.execute(LOAD_ALARM_SQL)
        alarm_defs = []
        alarm_states = {}
        for (id, sensor_id, agg, window, min, max, msg, state) in cur.fetchall():
            alarm_defs.append(AlarmDefinition(id=id, sensor_id=sensor_id, agg=Aggregate[agg],
                                              window=timedelta(seconds=window), min=min, max=max,
                                              message=msg))
            alarm_states[id] = AlarmState[state]
        return (alarm_defs, alarm_states)

UPDATE_STATE_SQL = 'UPDATE alarms SET state=? where id=?'
def update_state(id:str, new_state:AlarmState):
    with closing(conn.cursor()) as cur:
        cur.execute(UPDATE_STATE_SQL, (new_state.name, id))

# Generates a SQL query to evaluate a given definition        
def gen_sql(d:AlarmDefinition):
    sql = f'SELECT {d.agg.name}(value) FROM raw WHERE time BETWEEN ? and ?'
    if d.sensor_id is not None:
        sql = sql + ' AND sensor_id=?'
    return sql


# Computes the current state and value of this alarm
def evaluate_alarm(now, d:AlarmDefinition):
    with closing(conn.cursor()) as cur:
        sql = gen_sql(d)
        params = (now-d.window, now, d.sensor_id)
        if d.sensor_id is None:
            params = params[:2]
        logging.debug(f'Executing {sql} with {params}')
        cur.execute(sql, params)
        value = cur.fetchone()[0]

        if value is None:
            state = AlarmState.UNKNOWN
        elif d.min is not None and value < d.min:
            state = AlarmState.TOO_LOW
        elif d.max is not None and value > d.max:
            state = AlarmState.TOO_HIGH
        else:
            state = AlarmState.HEALTHY    

        return (state, value)

# Evaluates all alarms and queues emails as necessary
@repeat(every(5).minutes)
def evaluate_alarms():
    logging.info('Evaluating alarms')
    now = datetime.now(timezone.utc)
    alarm_defs, alarm_states = load_alarms()
    for d in alarm_defs:
        (state, value) = evaluate_alarm(now, d)
        logging.debug(f'{d.id} {state.name} {value}')
        old_state = alarm_states[d.id]
        if state != old_state:
            logging.error(f'ALARM {d.id} old_state={old_state.name} new_state={state.name} '\
                          f'now={now.isoformat()}')
            mail_queue.append(generate_email(d, now, old_state, state, value))
            update_state(d.id, state)

# Convert time delta to "3d5h4m32s" format
def format_time_delta(t:timedelta) -> str:
    ts = int(t.total_seconds())
    d = ts // 84600
    ts = ts % 86400
    h = ts // 3600
    ts = ts % 3600
    m = ts // 60
    s = ts % 60

    ret = ""
    if d > 0:
        ret = ret + f'{d}d '
    if h > 0:
        ret = ret + f'{h}h '
    if m > 0:
        ret = ret + f'{m}m '
    if s > 0 or t.total_seconds() == 0:
        ret = ret + f'{s}s '
        
    return ret.strip()

# Return 2 digits of precision or None
def format_value(v:float) -> str:
    if v is None:
        return 'No data'
    else:
        return f'{v:.2f}'

EMAIL_CSS = """
th {
    display: table-cell;
    vertical-align: inherit;
    font-weight: bold;
    text-align: left;
}
.code {
    font-family: monospace
}
"""

# Composes an email to tell the user what happened        
def generate_email(d:AlarmDefinition, now, old_state, new_state, value):
    
    plain = f"""The alarm {d.id} has transitioned from {old_state.name} to {new_state.name}.
    
Time:\t\t{now:%m/%d/%Y %H:%M:%S UTC}
Value:\t\t{format_value(value)}
Topic:\t\t{topics_by_id.get(d.sensor_id, 'Unknown')}
Aggregate:\t{d.agg.name}
Window:\t\t{format_time_delta(d.window)}
Min Allowed:\t{format_value(d.min)}
Max Allowed:\t{format_value(d.max)}
""";
    plain_part = MIMEText(plain, 'plain')
    
    html = f"""<html><head><style>{EMAIL_CSS}</style></head><body>
    <p>The alarm <span class=code>{d.id}</span> has transitioned from
    <span class=code>{old_state.name}</span> to <span class=code>{new_state.name}</span>.</p>
    <table>
    <tr><th>Time:</td><td>{now:%m/%d/%Y %H:%M:%S UTC}</td></tr>
    <tr><th>Value:</td><td>{format_value(value)}</td></tr>
    <tr><th>Topic:</td><td>{topics_by_id.get(d.sensor_id, 'Unknown')}</td></tr>
    <tr><th>Aggregate:</td><td>{d.agg.name}</td></tr>
    <tr><th>Window:</td><td>{format_time_delta(d.window)}</td></tr>
    <tr><th>Min Allowed:</td><td>{format_value(d.min)}</td></tr>
    <tr><th>Max Allowed:</td><td>{format_value(d.max)}</td></tr>
    </table>
    </body></html>""";    
    html_part = MIMEText(html, 'html')
    
    msg = MIMEMultipart('alternative')
    msg.attach(plain_part)
    msg.attach(html_part)
    msg['Subject'] = f'{new_state.name}: {d.message}'
    msg['From'] = email_sender
    msg['To'] = ', '.join(email_recipients)
    return msg
