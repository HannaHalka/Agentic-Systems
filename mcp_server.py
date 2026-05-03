from fastmcp import FastMCP
from github_api import GitHubAPI

mcp = FastMCP("Questions Management Server")


# RESPONSE DATA FORMAT UNCHECKED
@mcp.resource("issues://{issue_number}")
def get_issue_resource(owner, repo, issue_number) -> str:
    """Get a specific issue from the specified repository as a resource"""
    try:
        issue = GitHubAPI().get_issue(owner=owner, repo=repo, issue_number=issue_number)

        if not issue.data:
            return "No issue found."

        return issue.data
    except Exception as e:
        return f"Error retrieving issues: {str(e)}"


@mcp.prompt()
def list_all_issues(owner, repo) -> str:
    """Generate a formatted list all issues from the specified repository"""
    try:
        issues = GitHubAPI().list_repository_issues(owner=owner, repo=repo, state=None)

        if not issues.data:
            return "No issues found for the repository."

        formatted_issues = []
        for i, issue in enumerate(issues.data, 1):
            formatted_issues.append(
                f"{i}. ID: {issue.id}\n"
                f"    Author: {issue.author_id}\n"
                f"    Body: {issue.body}\n"
            )

        result = f"Found {len(issues.data)} issues:\n\n" + "\n".join(formatted_issues)

        return result
    except Exception as e:
        return f"Error retrieving issues: {str(e)}"


mcp.run()
