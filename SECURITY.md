# Security Policy

Local deterministic scanning only.

## GitHub access

GitHub activity collection uses **secure local authentication only** via the
GitHub CLI (`gh`) or an environment token. The runtime:

- requires an authenticated `gh` session (`gh auth status`) or `GITHUB_TOKEN` /
  fine-grained PAT passed through the environment;
- **fails closed** when authentication is missing
  (`{"authenticated": false, "collection_errors": ["gh_auth_missing"]}`);
- never prints tokens, never writes secrets to artifacts, and stores only
  computed activity metrics.

Forbidden and never performed: hardcoded tokens, tokens committed in `.env`,
browser cookie extraction, password prompts stored in logs, credential dumping.

Report vulnerabilities privately to the maintainer.
