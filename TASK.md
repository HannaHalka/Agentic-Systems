Data sources (no API key required for low-volume use; students may authenticate with
a personal token to raise rate limits):
- GitHub REST API (https://docs.github.com/en/rest) for issues, pull requests,
comments, labels, and commits of any public repository.

The assignment will fix a list of 5 mid-sized public repositories (between roughly 500
and 5000 open+closed issues) as the evaluation target. The exact list will be published
together with the starter evaluation set. You may not use additional repositories for
evaluation.

Task shape. The agent receives an issue (by URL or id) plus the repository context and
must produce a structured triage report. Examples of task types your evaluation set
should cover:

- Classify an issue into one of: bug, feature request, question, documentation, or
duplicate, with a short justification citing specific content from the issue or linked
issues.
- Given an issue, find up to 3 likely duplicate or closely related issues already filed in
the same repository, and explain the relationship.
- Given a bug report, identify the most probable area of the codebase affected (file
paths or module names) using the issue text plus repository search. Do not run the
code.
- Given an open issue older than 6 months, summarize its current state, outstanding
questions, and what decision is needed to move it forward.

Why this track is non-trivial. Labels are not ground truth — issues are often mislabeled
by the humans who filed them. The agent must read linked issues and PRs, reconcile partial information, and refuse to guess when evidence is thin. Duplicate detection in
particular forces the agent to run multiple search strategies (title keywords,
error-message substrings, labels) rather than a single embedding lookup.

If you prefer a local model, use one of the following via Ollama or vLLM on your own
hardware:
- Qwen 2.5 7B or 14B Instruct — currently the strongest small open-weight option for
tool use.
