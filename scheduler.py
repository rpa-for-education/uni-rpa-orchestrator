from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import requests
import datetime
from db import SESSION
from models import RunLog, Schedule
from github_trigger import trigger_github_action

scheduler = BackgroundScheduler()

def run_bot(app_name, action, schedule_id=None):
    session = SESSION()
    try:
        log_entry = RunLog(
            schedule_id=schedule_id,
            start_time=datetime.datetime.utcnow(),
            status="RUNNING",
            app_name=app_name or "unknown"
        )
        session.add(log_entry)
        session.commit()

        if app_name in ['ai', 'kbs']:
            success, message = trigger_github_action(app_name, action)
            log_entry.end_time = datetime.datetime.utcnow()
            if success:
                log_entry.status = "SUCCESS"
                log_entry.output = message
            else:
                log_entry.status = "FAILED"
                log_entry.error_message = message
        else:
            api_endpoint = session.query(Schedule).filter_by(id=schedule_id).first().api_endpoint
            response = requests.get(api_endpoint, timeout=30)
            response.raise_for_status()
            log_entry.end_time = datetime.datetime.utcnow()
            log_entry.status = "SUCCESS"
            log_entry.output = response.text

        session.add(log_entry)
        session.commit()
    except Exception as e:
        log_entry.end_time = datetime.datetime.utcnow()
        log_entry.status = "FAILED"
        log_entry.error_message = str(e)
        session.add(log_entry)
        session.commit()
    finally:
        session.close()

def load_schedules():
    session = SESSION()
    try:
        schedules = session.query(Schedule).filter_by(active=True).all()
        for schedule in schedules:
            scheduler.add_job(
                run_bot,
                trigger=CronTrigger.from_crontab(schedule.schedule),
                args=[None, 'start', schedule.id]
            )
    finally:
        session.close()

def start_scheduler():
    scheduler.start()