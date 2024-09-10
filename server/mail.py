import logging
import smtplib
from common import mail_queue, config_map
from schedule import repeat, every

@repeat(every().minute)
def send_mail():
    cfg = config_map['email']
    if mail_queue:
        # TODO - Exception handling
        with smtplib.SMTP_SSL(cfg['smtp_host'], cfg['smtp_port']) as smtp_server:
            smtp_server.login(cfg['username'], cfg['password'])
            while mail_queue:
                msg = mail_queue.pop()
                logging.debug(f'Sending email: {msg}')
                smtp_server.sendmail(cfg['sender'], cfg['recipients'], msg.as_string())
