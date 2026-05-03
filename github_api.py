import json
import requests
from dotenv import load_dotenv
import base64
from urllib.parse import urlparse, unquote

api_url = "https://api.github.com"
load_dotenv()


def github_file_url(url):
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")

    # Expected example:
    # owner      / repo            / blob / branch     / path to file
    # HannaHalka / Agentic-Systems / blob / github-api / github_api.py
    if len(parts) < 5:
        raise ValueError("Invalid GitHub file URL")

    owner = parts[0]
    repo = parts[1]
    ref = parts[3]

    file_path = "/".join(parts[4:])
    file_path = unquote(file_path)

    m = {
        "owner": owner,
        "repo": repo,
        "ref": ref,
        "file_path": file_path,
    }
    return m


class GitHubAPI:
    def __init__(self, base_url=api_url, api_version="2026-03-10"):
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

    def get_repository_file(self, owner, repo, file_path, ref):
        params = {}

        response = self._get(
            path=f"/repos/{owner}/{repo}/contents/{file_path}",
            params=params
        )

        if response.get("error"):
            return response

        data = response.get("data")

        encoded_content = data.get("content", "")

        clean_content = encoded_content.replace("\n", "")
        decoded_bytes = base64.b64decode(clean_content)
        decoded_text = decoded_bytes.decode("utf-8", errors="replace")

        return {
            "status": response.get("status"),
            "url": response.get("url"),
            "owner": owner,
            "repo": repo,
            "ref": ref,
            "path": data.get("path"),
            "name": data.get("name"),
            "sha": data.get("sha"),
            "size": data.get("size"),
            "content": decoded_text,
        }

    def get_repository_file_by_url(self, url):
        parsed = github_file_url(url)

        return self.get_repository_file(
            owner=parsed["owner"],
            repo=parsed["repo"],
            file_path=parsed["file_path"],
            ref=parsed["ref"],
        )


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


# client = GitHubAPI()
# url = "https://github.com/HannaHalka/Agentic-Systems/blob/github-api/github_api.py"
# result = client.get_repository_file_by_url(url)
# print(json.dumps(result, indent=2, ensure_ascii=False))
