# Security Policy

## Reporting a Vulnerability

If you discover a security vulnerability in IRDoc, please report it to **security@irdoc.io** rather than opening a public issue or pull request.

Please include as much of the following as you can:

- A description of the vulnerability and its potential impact
- Steps to reproduce it (a minimal proof of concept is ideal)
- The affected version/commit
- Any suggested remediation, if you have one

## Response

We aim to acknowledge new reports within 3 business days, and to release patches for confirmed critical vulnerabilities within 24 hours of confirmation. You'll be credited in the fix's release notes unless you'd prefer to stay anonymous.

## Supported Versions

IRDoc ships as a self-hosted application without long-term-support branches. Security fixes are released against the latest version on `main`; we recommend always running the most recent release.

## Scope

This policy covers the IRDoc application itself (`backend/`, `frontend/`, `installer/`) and its first-party GitHub Actions workflows. Vulnerabilities in third-party dependencies should be reported upstream, though we're happy to help coordinate — automated dependency scanning (Dependabot, CodeQL, OpenSSF Scorecard) already tracks known CVEs in our dependency tree.

## Automated Scanning

This repository runs CodeQL static analysis, secret scanning (Gitleaks), Dependabot dependency updates, and an [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/soc-irdoc/irdoc-app) assessment on every push. See the badges in [README.md](README.md) for current status.
