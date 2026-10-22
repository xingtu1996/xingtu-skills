# Security Policy

## Scope

This repository distributes Agent Skills (`SKILL.md` packages, helper scripts, and prompts). Skills are executable instructions for AI agents: they may direct an agent to run shell commands, read and write files, call network APIs, and handle credentials on the user's machine. Security reports about any of the following are in scope:

- Malicious or unsafe commands embedded in a skill or its scripts
- Prompt-injection paths (content a skill ingests that can hijack the agent)
- Hardcoded or leaked credentials, tokens, or private data in any file
- Unsafe defaults that perform destructive or irreversible actions without human confirmation
- Risks introduced by bundled third-party code or instructions

## Reporting a vulnerability

Please report privately rather than opening a public issue with exploit details:

1. Use GitHub's private vulnerability reporting for this repository (Security tab → "Report a vulnerability"), or
2. Contact the maintainer via the contact information on the GitHub profile of [@xingtu1996](https://github.com/xingtu1996).

Please include the affected skill name and path, a description of the risk, and reproduction steps if available. Never include real credentials or secrets in a report.

The maintainer reviews reports on a best-effort basis and aims to acknowledge within 7 days. Confirmed issues are fixed in the skill itself and noted in the change history; because skills are plain files, users should re-pull updated skills rather than relying on cached copies.

## Review principles for contributions

Third-party skill contributions are reviewed against these rules before merging:

- **No hardcoded secrets.** Credentials are read from environment variables or user-supplied secret files only, and never committed.
- **No silent destructive actions.** Deleting data, publishing, sending messages, or spending money requires an explicit human confirmation step in the skill's workflow.
- **Declared side effects.** A skill must state, in its description or body, what it executes, what it writes, and what network calls it makes.
- **Pinned, inspectable dependencies.** Helper scripts prefer the standard library and zero-dependency designs; any external dependency must be declared and justified.

## Supported versions

Only the latest state of the default branch is maintained. Skills are versioned through the repository's `marketplace.json` catalog and release history.
