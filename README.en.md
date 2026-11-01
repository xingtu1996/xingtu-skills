# XingTu Skills — English Guide

> Production Agent Skills for AI coding agents. Maintained by **行途 XingTu**.

The main [README](README.md) already contains an English overview followed by detailed Chinese documentation. This page is a stable English-language entry point rather than a separate, potentially stale inventory.

## What is included?

- Reusable Agent Skills in the `SKILL.md` format, with scripts and references where needed.
- Curated prompts and tooling for agent workflows.
- Integration guidance for Claude Code, Codex, Cursor and other compatible agents.

For the current skill count and catalog, use the repository's [`marketplace.json`](marketplace.json) and [`skills/`](skills/) directory; counts change as the collection evolves.

## Quick start

```bash
git clone https://github.com/xingtu1996/xingtu-skills.git
cd xingtu-skills
# Inspect a skill before installing or running it.
ls skills
```

Read the skill's `SKILL.md` and copy the selected skill folder into your agent's supported skills directory. Consult your agent's documentation for the destination path.

## Contributing and security

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a PR. Agent skills can execute commands or access sensitive data; review their instructions and scripts before use. Report security issues according to [SECURITY.md](SECURITY.md), not in a public issue.

## License

[MIT](LICENSE). See the [main README](README.md) for the full bilingual project description.
