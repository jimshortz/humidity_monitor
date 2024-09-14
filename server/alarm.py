import logging
from common import conn, config_map, mail_queue
from dataclasses import dataclass
from datetime import date, datetime, timezone, timedelta
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
    cur = conn.cursor()
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
    cur = conn.cursor()
    cur.execute(UPDATE_STATE_SQL, (new_state.name, id))
    
def gen_sql(d:AlarmDefinition):
    sql = f'SELECT {d.agg.name}(value) FROM raw WHERE time BETWEEN ? and ?'
    if d.sensor_id is not None:
        sql = sql + ' AND sensor_id=?'
    return sql

        
def evaluate_alarm(now, d:AlarmDefinition):
    cur = conn.cursor()
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

@repeat(every(5).minutes)
def evaluate_alarms():
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
           
        
def generate_email(d:AlarmDefinition, now, old_state, new_state, value):
    value_formatted = 'None' if value is None else f'{value:.2f}'
    body = f"""Alarm {d.id} has entered the {new_state.name} state (was {old_state.name}).
As of {now.isoformat()} value is {value_formatted}."""
    if d.min is not None:
        body = body + f'\nMinimum allowed is {d.min:.2f}.'

    if d.max is not None:
        body = body + f'\nMaximum allowed is {d.max:.2f}.'
    
    msg = MIMEText(body)
    msg['Subject'] = f'{new_state.name}: {d.message}'
    msg['From'] = email_sender
    msg['To'] = ', '.join(email_recipients)
    return msg
