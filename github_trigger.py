import requests
import os
from db import SESSION
from models import RunLog
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def trigger_github_action(app_name, action):
    logger.debug(f"Starting trigger_github_action: app_name={app_name}, action={action}")
    pat = os.getenv("GITHUB_PAT")
    if not pat:
        logger.error("GITHUB_PAT is not set")
        return False, "GITHUB_PAT is not set"

    repo = f"rpa-for-education/{app_name}"
    workflow_id = "auto_run.yml"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {
        "ref": "main",
        "inputs": {"action": action}
    }

    # Kiểm tra token trước
    try:
        logger.debug("Verifying GITHUB_PAT")
        test_response = requests.get("https://api.github.com/user", headers=headers, timeout=5)
        if test_response.status_code != 200:
            logger.error(f"Invalid GITHUB_PAT: {test_response.status_code} - {test_response.text}")
            return False, f"Invalid GITHUB_PAT: {test_response.status_code} - {test_response.text}"
        logger.debug("GITHUB_PAT verified")
    except Exception as e:
        logger.error(f"Failed to verify GITHUB_PAT: {str(e)}")
        return False, f"Failed to verify GITHUB_PAT: {str(e)}"

    session = SESSION()
    try:
        log_entry = RunLog(
            app_name=app_name,
            start_time=datetime.utcnow(),
            status="RUNNING"
        )
        session.add(log_entry)
        try:
            session.commit()
            logger.debug(f"Log entry created: id={log_entry.id}")
        except Exception as commit_error:
            logger.error(f"Failed to commit log entry: {str(commit_error)}")
            raise

        logger.debug(f"Sending request to GitHub API: url={url}, data={data}")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        log_entry.end_time = datetime.utcnow()
        logger.debug(f"GitHub API response: status_code={response.status_code}")

        if response.status_code == 204:
            log_entry.status = "SUCCESS"
            log_entry.output = f"Triggered {action} for {app_name}"
            session.add(log_entry)
            try:
                session.commit()
                logger.debug("Workflow triggered successfully")
            except Exception as commit_error:
                logger.error(f"Failed to commit success log: {str(commit_error)}")
                raise
            return True, "Workflow triggered successfully"
        else:
            log_entry.status = "FAILED"
            log_entry.error_message = f"Failed to trigger workflow: {response.status_code} - {response.text}"
            session.add(log_entry)
            try:
                session.commit()
                logger.error(log_entry.error_message)
            except Exception as commit_error:
                logger.error(f"Failed to commit error log: {str(commit_error)}")
                raise
            return False, log_entry.error_message
    except Exception as e:
        logger.error(f"Error in trigger_github_action: {str(e)}")
        log_entry.end_time = datetime.utcnow()
        log_entry.status = "FAILED"
        log_entry.error_message = f"Request failed: {str(e)}"
        session.add(log_entry)
        try:
            session.commit()
        except Exception as commit_error:
            logger.error(f"Failed to commit error log: {commit_error)}")
        return False, log_entry.error_message
    finally:
        try:
            session.close()
        except Exception as close_error:
            logger.error(f"Failed to close session: {str(close_error)}")
        logger.debug("Session closed")

def trigger_github_ai_action():
    return trigger_github_action('ai', 'start')

def trigger_github_kbs_action():
    return trigger_github_action('kbs', 'start')