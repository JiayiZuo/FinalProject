from celery_app import celery
from flask_mail import Message
from app import mail, app
import pymysql
from datetime import datetime
from config import *

def get_db_connection():
    return pymysql.connect(
        host=MYSQL_HOST,
        user=MYSQL_USER,
        password=MYSQL_PASSWORD,
        database=MYSQL_DB,
        cursorclass=pymysql.cursors.DictCursor
    )

@celery.task(name='tasks.check_and_send_reminders')
def check_and_send_reminders():
    now = datetime.now().strftime('%H:%M')
    today = datetime.now().date()

    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM medication_reminder WHERE is_active = 1 AND start_date <= %s AND end_date >= %s
            """, (today, today))
            reminders = cursor.fetchall()

            for reminder in reminders:
                times = [t.strip() for t in reminder['reminder_times'].split(',')]
                if now in times and reminder.get('email'):
                    send_email_reminder(reminder)

def send_email_reminder(reminder):
    with app.app_context():
        msg = Message(
            subject='💊 用药提醒',
            recipients=[reminder['email']],
            body=f"请按时服用您的药物：{reminder['medicine_name']}。提醒时间：{datetime.now().strftime('%H:%M')}"
        )
        mail.send(msg)
