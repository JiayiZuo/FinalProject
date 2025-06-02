from celery import Celery
from config import *

def make_celery(app_name=__name__):
    return Celery(app_name, broker=CELERY_BROKER_URL, backend=CELERY_RESULT_BACKEND)

celery = make_celery()
celery.conf.update(
    timezone='Asia/Shanghai',
    enable_utc=False,
    beat_schedule={
            'send-medicine-reminders-every-minute': {
                'task': 'tasks.check_and_send_reminders',
                'schedule': 60.0,
            },
    }
)

import tasks