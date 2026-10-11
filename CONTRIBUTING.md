# Contributing to IRDoc

Thanks for taking the time to help. IRDoc is a small project, so every bug report, fix and idea makes a real difference.

This guide explains how to report problems, suggest features and send code. The same guide is published at [docs.irdoc.io/contributing](https://docs.irdoc.io/contributing).

---

## Ways to contribute

- Report a bug
- Suggest a feature or an improvement
- Fix a bug or build a feature
- Improve the documentation ([irdoc-docs](https://github.com/soc-irdoc/irdoc-docs))
- Sponsor the project (see [Sponsorship](#sponsorship))

---

## Security vulnerabilities

Do not report security problems in a public issue, pull request or discussion.

Send them to **security@irdoc.io** instead. See [SECURITY.md](SECURITY.md) for what to include and how fast we respond.

---

## Reporting a bug

Open an issue on [GitHub Issues](https://github.com/soc-irdoc/irdoc-app/issues). Search first, the bug may already be reported.

A good bug report has:

- The IRDoc version (shown at the bottom of the left navigation and in Settings)
- How you run it (installer wizard, Docker Compose, behind a load balancer, and so on)
- The steps to reproduce it
- What you expected and what happened instead
- Logs or screenshots, if they help

IRDoc holds incident data. Before you paste logs, screenshots or exports, remove anything sensitive: real IOCs from a customer, hostnames, user names, API keys, passwords and tokens. If the bug only shows with real data, describe it and we will find another way to reproduce it.

---

## Suggesting a feature

Open an issue and describe the problem you want to solve, not only the solution. "During an incident I have to do X and it takes too long" is more useful than "add a button for X". It helps us find the right fix and fit it with the rest of the product.

---

## Before you write code

For anything bigger than a small fix, open an issue first, or comment on an existing one, and say you want to work on it. This avoids two people doing the same work and avoids a pull request that does not fit the plan for the project.

Small fixes (typos, an obvious bug, a missing test) can go straight to a pull request.

---

## Development setup

Follow the [Development Setup](https://docs.irdoc.io/#contributing/development-setup) guide. It covers the backend (Python 3.12, FastAPI), the frontend (Node.js 20+, React) and the PostgreSQL and Redis containers you need.

The [Architecture Overview](https://docs.irdoc.io/#contributing/architecture) and [Adding Integrations](https://docs.irdoc.io/#contributing/adding-integrations) pages are worth reading before a larger change.

---

## Making a change

### Branches

Fork the repository and create a branch from `main`. Name it after the type of change and the issue number:

```
fix/101-timeline-render-loop
feat/88-shodan-enrichment
docs/contributing-guide
```

### Commits

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
fix(timeline): stop the edit modal from re-rendering in a loop (#101)
feat(integrations): add Shodan enrichment
docs: explain the backup retention setting
```

Common types: `feat`, `fix`, `docs`, `test`, `refactor`, `ci`, `chore`. Keep each commit focused on one thing, and explain the why in the commit body when it is not obvious.

### Code style

- Match the code around your change: naming, structure and comment style.
- Backend code must pass `ruff check .`
- Frontend code must pass `npm run lint` and `npm run type-check`
- Use a plain hyphen "-" in UI text, messages and reports, not an em dash or an en dash.

### Tests

Add or update tests for what you change. A bug fix should come with a test that fails without the fix.

Run the same checks CI runs before you open the pull request:

```bash
# Backend
cd backend
ruff check .
pytest

# Frontend
cd frontend
npm run type-check
npm run lint
npm test
npm run build

# Installer (only if you changed installer/)
pip install -r installer/requirements.txt
python -m pytest installer/tests
```

### Database changes

If you change a model, add an Alembic migration (`alembic revision --autogenerate -m "short description"`), read it before you commit it, and check that `alembic upgrade head` works on a fresh database and on an existing one.

### Dependencies

Add new dependencies only when they are really needed. For the backend, add the package to `backend/requirements.txt` and regenerate the lock file with hashes:

```bash
cd backend
pip-compile --generate-hashes --output-file=requirements.lock.txt requirements.txt
```

CI fails if `requirements.lock.txt` is out of sync with `requirements.txt`. For the frontend, commit the updated `package-lock.json`.

### Changelog and docs

- If your change is visible to users or admins, add a line to [CHANGELOG.md](CHANGELOG.md) under `[Unreleased]`, in the right group (Added, Changed, Fixed, Removed). Write it for the person running IRDoc, not for a developer, and add the issue number at the end, for example `(#101)`.
- If your change affects how something is installed, configured or used, update the matching page in [irdoc-docs](https://github.com/soc-irdoc/irdoc-docs) too, in a separate pull request there.

---

## Opening a pull request

- Keep a pull request to one change. Two unrelated fixes are easier to review as two pull requests.
- Link the issue in the description, for example `Fixes #101`.
- Explain what changed and how you tested it.
- Add screenshots for UI changes, in both the dark and the light theme if the change is visual.
- Make sure CI passes (backend, frontend and installer checks, CodeQL and secret scanning).
- Never commit secrets, real incident data or `.env` files.

A maintainer will review it. We may ask for changes. That is a normal part of the process, not a rejection. If a pull request is waiting for you and goes quiet for a long time, we may close it, and you can reopen it whenever you are ready.

---

## License

IRDoc's core is licensed under [AGPL-3.0](LICENSE.md). By sending a contribution, you agree that it is licensed under the same license.

---

## Sponsorship

If IRDoc is useful to you or your organization and you want to support its development, you can sponsor it on [GitHub Sponsors](https://github.com/sponsors/petruspinu) or [Ko-fi](https://ko-fi.com/petruspinu).

| Tier | Monthly | What it supports |
|------|---------|------------------|
| Supporter | $5 | Open-source security tooling, and development and infrastructure costs |
| Builder | $10 | Everything in Supporter, plus new features, integrations, documentation and maintenance |
| Project Supporter | $20 | Everything in Builder, plus larger features and the long-term development of the project |

Thank you, whatever way you choose to help.
