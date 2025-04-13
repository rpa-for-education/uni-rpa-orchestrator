import requests
import os
from db import SESSION
from models import RunLog
from datetime import datetime

def trigger_github_action(app_name, action):
    """
    Kích hoạt GitHub Action cho ứng dụng.
    Args:
        app_name: 'ai' hoặc 'kbs'
        action: 'start' hoặc 'stop'
    Returns:
        tuple: (success: bool, message: str)
    """
    pat = os.getenv("GITHUB_PAT")
    if not pat:
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
        "inputs": {"action": action}  # Truyền action vào workflow
    }

    session = SESSION()
    try:
        log_entry = RunLog(
            app_name=app_name,
            start_time=datetime.utcnow(),
            status="RUNNING"
        )
        session.add(log_entry)
        session.commit()

        response = requests.post(url, headers=headers, json=data)
        log_entry.end_time = datetime.utcnow()
        if response.status_code == 204:
            log_entry.status = "SUCCESS"
            log_entry.output = f"Triggered {action} for {app_name}"
            session.add(log_entry)
            session.commit()
            return True, "Workflow triggered successfully"
        else:
            log_entry.status = "FAILED"
            log_entry.error_message = f"Failed to trigger workflow: {response.status_code} - {response.text}"
            session.add(log_entry)
            session.commit()
            return False, log_entry.error_message
    except Exception as e:
        log_entry.end_time = datetime.utcnow()
        log_entry.status = "FAILED"
        log_entry.error_message = f"Request failed: {str(e)}"
        session.add(log_entry)
        session.commit()
        return False, log_entry.error_message
    finally:
        session.close()

# Giữ hàm cũ cho tương thích
def trigger_github_ai_action():
    return trigger_github_action('ai', 'start')

def trigger_github_kbs_action():
    return trigger_github_action('kbs', 'start')