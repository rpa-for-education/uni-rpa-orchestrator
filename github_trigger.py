import requests
import os
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

    # Kiểm tra token
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

    try:
        logger.debug(f"Sending request to GitHub API: url={url}, action={action}")
        response = requests.post(url, headers=headers, json=data, timeout=10)
        logger.debug(f"GitHub API response: status_code={response.status_code}")

        if response.status_code == 204:
            message = f"Triggered {action} for {app_name}"
            logger.debug(message)
            return True, message
        else:
            error_msg = f"Failed to trigger workflow: {response.status_code} - {response.text}"
            logger.error(error_msg)
            return False, error_msg
    except Exception as e:
        logger.error(f"Error in trigger_github_action: {str(e)}")
        return False, f"Request failed: {str(e)}"

def trigger_github_ai_action():
    return trigger_github_action('ai', 'start')

def trigger_github_kbs_action():
    return trigger_github_action('kbs', 'start')