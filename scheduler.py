from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import requests
import datetime
from db import SessionFactory
from models import RunLog, Schedule

scheduler = BackgroundScheduler()


def run_bot(api_endpoint, schedule_id):
    session = SessionFactory()
    log_entry = RunLog(
        schedule_id=schedule_id,
        start_time=datetime.datetime.utcnow(),
        status="RUNNING"
    )
    session.add(log_entry)
    session.commit()

    try:
        response = requests.get(api_endpoint, timeout=30)
        response.raise_for_status()
        log_entry.end_time = datetime.datetime.utcnow()
        log_entry.status = "SUCCESS"
        log_entry.output = response.text
    except Exception as e:
        log_entry.end_time = datetime.datetime.utcnow()
        log_entry.status = "FAILED"
        log_entry.error_message = str(e)

    session.add(log_entry)
    session.commit()
    session.close()


def load_schedules():
    session = SessionFactory()
    schedules = session.query(Schedule).filter_by(active=True).all()
    for schedule in schedules:
        scheduler.add_job(
            run_bot,
            trigger=CronTrigger.from_crontab(schedule.schedule),
            args=[schedule.api_endpoint, schedule.id]
        )
    session.close()


def start_scheduler():
    scheduler.start()