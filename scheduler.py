from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import requests
import datetime
from db import SESSION
from models import RunLog, Schedule
from github_trigger import trigger_github_action
import logging

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler()

def run_bot(app_name, action, schedule_id=None):
    logger.debug(f"Starting run_bot: app_name={app_name}, action={action}, schedule_id={schedule_id}")
    session = SESSION()
    try:
        log_entry = RunLog(
            schedule_id=schedule_id,
            start_time=datetime.datetime.utcnow(),
            status="RUNNING",
            app_name=app_name or "unknown"
        )
        session.add(log_entry)
        try:
            session.commit()
            logger.debug(f"Log entry created: id={log_entry.id}")
        except Exception as commit_error:
            logger.error(f"Failed to commit log entry: {str(commit_error)}")
            raise

        if app_name in ['ai', 'kbs']:
            logger.debug(f"Calling trigger_github_action for {app_name}")
            success, message = trigger_github_action(app_name, action)
            logger.debug(f"trigger_github_action result: success={success}, message={message}")
            log_entry.end_time = datetime.datetime.utcnow()
            if success:
                log_entry.status = "SUCCESS"
                log_entry.output = message
            else:
                log_entry.status = "FAILED"
                log_entry.error_message = message
        else:
            api_endpoint = session.query(Schedule).filter_by(id=schedule_id).first().api_endpoint
            logger.debug(f"Calling API endpoint: {api_endpoint}")
            response = requests.get(api_endpoint, timeout=30)
            response.raise_for_status()
            log_entry.end_time = datetime.datetime.utcnow()
            log_entry.status = "SUCCESS"
            log_entry.output = response.text

        session.add(log_entry)
        try:
            session.commit()
            logger.debug(f"Log entry updated: status={log_entry.status}")
        except Exception as commit_error:
            logger.error(f"Failed to commit log update: {str(commit_error)}")
            raise
    except Exception as e:
        logger.error(f"Error in run_bot: {str(e)}")
        log_entry.end_time = datetime.datetime.utcnow()
        log_entry.status = "FAILED"
        log_entry.error_message = str(e)
        session.add(log_entry)
        try:
            session.commit()
        except Exception as commit_error:
            logger.error(f"Failed to commit error log: {str(commit_error)}")
        raise
    finally:
        try:
            session.close()
        except Exception as close_error:
            logger.error(f"Failed to close session: {str(close_error)}")
        logger.debug("Session closed")

def load_schedules():
    logger.debug("Loading schedules")
    session = SESSION()
    try:
        schedules = session.query(Schedule).filter_by(active=True).all()
        for schedule in schedules:
            scheduler.add_job(
                run_bot,
                trigger=CronTrigger.from_crontab(schedule.schedule),
                args=[None, 'start', schedule.id]
            )
            logger.debug(f"Added schedule: id={schedule.id}, bot_name={schedule.bot_name}")
    except Exception as e:
        logger.error(f"Error loading schedules: {str(e)}")
        raise
    finally:
        try:
            session.close()
        except Exception as close_error:
            logger.error(f"Failed to close session: {str(close_error)}")
        logger.debug("Schedules loaded")

def start_scheduler():
    logger.debug("Starting scheduler")
    try:
        scheduler.start()
        logger.debug("Scheduler started")
    except Exception as e:
        logger.error(f"Error starting scheduler: {str(e)}")
        raise