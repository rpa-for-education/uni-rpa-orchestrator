import requests
import os

def trigger_github_action():
    pat = os.getenv("GITHUB_PAT")
    if not pat:
        return False, "GITHUB_PAT is not set"
    repo = "rpa-for-education/ai"
    workflow_id = "auto_run.yml"
    url = f"https://api.github.com/repos/{repo}/actions/workflows/{workflow_id}/dispatches"
    headers = {
        "Authorization": f"Bearer {pat}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    data = {"ref": "main"}
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 204:
            return True, "Workflow triggered successfully"
        else:
            return False, f"Failed to trigger workflow: {response.status_code} - {response.json()}"
    except Exception as e:
        return False, f"Request failed: {str(e)}"