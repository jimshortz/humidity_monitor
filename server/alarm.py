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

alarm_defs = [
    AlarmDefinition(
        id='dataflow',
        agg=Aggregate.COUNT,
        min=1,
        window=timedelta(minutes=5),
        message="Data flow"
    ),
    AlarmDefinition(
        id='humidity',
        sensor_id=1,
        agg=Aggregate.AVG,
        min=20,
        max=50,
        window=timedelta(minutes=15),
        message='Humidity'
    ),
    AlarmDefinition(
        id='dehumid',
        sensor_id=3,
        agg=Aggregate.MAX,
        min=200,
        window=timedelta(minutes=60),
        message='Dehumidfier 1hr'
    ),        
]

alarm_state = {d.id: AlarmState.UNKNOWN for d in alarm_defs}

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

@repeat(every().minute)
def evaluate_alarms():
    now = datetime.now(timezone.utc)
    for d in alarm_defs:
        (state, value) = evaluate_alarm(now, d)
        logging.info(f'{d.id} {state.name} {value}')
        old_state = alarm_state[d.id]
        if state != old_state:
            logging.error(f'ALARM {d.id} old_state={old_state.name} ' \
                          'new_state={state.name} now={now.isoformat())')
            mail_queue.append(generate_email(d, now, old_state, state, value))
            alarm_state[d.id] = state
           
        
def generate_email(d:AlarmDefinition, now, old_state, new_state, value):
    # TODO - reduce decimal points
    body = f"""Alarm {d.id} has entered the {new_state.name} state (was {old_state.name}).
As of {now.isoformat()} value is {value}."""
    if d.min is not None:
        body = body + f'\nMinimum allowed is {d.min:.2f}.'

    if d.max is not None:
        body = body + f'\nMaximum allowed is {d.max:.2f}.'
    
    msg = MIMEText(body)
    msg['Subject'] = f'{new_state.name}: {d.message}'
    msg['From'] = email_sender
    msg['To'] = ', '.join(email_recipients)
    return msg
