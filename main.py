from fastapi import FastAPI, HTTPException, Query
from typing import Optional
import requests
from requests.auth import HTTPBasicAuth

app = FastAPI()

@app.get("/simplified-jira-issues")
def get_simplified_issues(
    jira_url: str = Query(..., description="Jira API URL, e.g., https://your-domain.atlassian.net/rest/api/2/search?jql=project=KEY&expand=names,schema"),
    email: str = Query(..., description="Your Jira email address"),
    api_token: str = Query(..., description="Your Jira API token")
):
    try:
        response = requests.get(jira_url, auth=HTTPBasicAuth(email, api_token))

        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch data from Jira")

        data = response.json()

        # Process and simplify JSON
        table_data = []
        for issue in data.get("issues", []):
            fields = issue.get("fields", {})

            issue_type = fields.get("issuetype", {}).get("name", "")
            parent_key = (
                None if issue_type == "Epic"
                else fields.get("parent", {}).get("key", "N/A")
            )

            entry = {
                "issue_key": issue.get("key", ""),
                "summary": fields.get("summary", ""),
                "issue_type": issue_type,
                "parent": parent_key,
                "status": fields.get("status", {}).get("name", ""),
                "assignee": fields.get("assignee", {}).get("displayName", "N/A") if fields.get("assignee") else "N/A",
                "reporter": fields.get("reporter", {}).get("displayName", "N/A") if fields.get("reporter") else "N/A",
            }

            table_data.append(entry)

        return {"data": table_data}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
