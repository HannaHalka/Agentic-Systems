import requests
from dotenv import load_dotenv
import json


api_url = "https://api.github.com"
load_dotenv()


class GitHubAPI:
    def __init__(self, base_url=api_url, api_version="v0.0"):
        self.base_url = base_url.rstrip("/")
        self.api_version = api_version

    def _headers(self):
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": self.api_version,
            "User-Agent": "github-issue-triage-agent",
        }

        return headers

    def _get(self, path, params=None):
        url = f"{self.base_url}{path}"
        response = requests.get(url, headers=self._headers(), params=params)

        result = {
            "status": response.status_code,
            "url": response.url,
            "data": response.json(),
        }

        if not response.ok:
            result["error"] = self._classify_error(response.status_code)

        return result

    @staticmethod
    def _classify_error(status_code):
        if status_code == 403: return "forbidden_or_rate_limited"
        if status_code == 404: return "not_found"
        if status_code == 410: return "gone"
        if status_code == 422: return "validation_failed"
        if status_code >= 500: return "github_server_error"
        return "http_error"

    def get_issue(self, owner, repo, issue_number):
        issue = self._get(f"/repos/{owner}/{repo}/issues/{issue_number}")
        return issue

    # from Evaluation and Trajectory Analysis "At least 30 tasks you design yourself"
    def get_issue_comments(self, owner, repo, issue_number, per_page=30, page=1):
        issue_comments = self._get(
            path=f"/repos/{owner}/{repo}/issues/{issue_number}/comments",
            params={
                "per_page": per_page,
                "page": page,
            })
        return issue_comments

    def list_repository_issues(self, owner, repo, state="open", per_page=30, page=1):
        repository_issues = self._get(
            path=f"/repos/{owner}/{repo}/issues",
            params={
                "state": state,
                "per_page": per_page,
                "page": page,
            })
        return repository_issues

    def search_issues(self, owner, repo, query, state=None, per_page=30, page=1):
        q = f"repo:{owner}/{repo} is:issue {query}"
        if state:
            q += f" state:{state}"

        issue = self._get(
            path="/search/issues",
            params={
                "q": q,
                "per_page": per_page,
                "page": page,
            })
        return issue


def execute_function(function_name: str, arguments: dict[str, any], client: GitHubAPI) -> str:
    """Execute the function call and return result as string"""
    if function_name == "get_issue":
        result = client.get_issue(**arguments)
    elif function_name == "get_issue_comments":
        result = client.get_issue_comments(**arguments)
    elif function_name == "list_repository_issues":
        result = client.list_repository_issues(**arguments)
    elif function_name == "search_issues":
        result = client.search_issues(**arguments)
    else:
        return f"Unknown function: {function_name}"

    return json.dumps(result, indent=2)
