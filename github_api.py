import logging

import requests
from dotenv import load_dotenv


api_url = "https://api.github.com"

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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
