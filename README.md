# IRDoc - Incident Response Documentation Platform

> Timeline-first IR documentation with visual report builder, SharePoint auto-sync, and AI-assisted summaries.

[![CI](https://github.com/soc-irdoc/irdoc-app/actions/workflows/ci.yml/badge.svg)](https://github.com/soc-irdoc/irdoc-app/actions/workflows/ci.yml)
[![CodeQL](https://github.com/soc-irdoc/irdoc-app/actions/workflows/codeql.yml/badge.svg)](https://github.com/soc-irdoc/irdoc-app/actions/workflows/codeql.yml)
[![Secret Scan](https://github.com/soc-irdoc/irdoc-app/actions/workflows/secret-scan.yml/badge.svg)](https://github.com/soc-irdoc/irdoc-app/actions/workflows/secret-scan.yml)
[![OpenSSF Scorecard](https://api.securityscorecards.dev/projects/github.com/soc-irdoc/irdoc-app/badge)](https://scorecard.dev/viewer/?uri=github.com/soc-irdoc/irdoc-app)
[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL_3.0-blue.svg)](LICENSE)

---

## What is IRDoc?

IRDoc is a **self-hostable, open-core incident response documentation platform** for SOC analysts, IR engineers, and MSSPs.

It gives your team one structured workspace to document an incident from first detection to final report - instead of switching between a ticket system, a Word document, and a SharePoint folder.

**Core promise:** *Document incidents the way you actually investigate them - fast, structured, and reportable in one click.*

- **Timeline-first workspace** - chronological event log across detection, analysis, containment, evidence, and comms
- **IOC management** - track and auto-detect IPs, domains, hashes, emails, and URLs
- **Evidence attachments** - drag-and-drop or paste screenshots straight into the timeline
- **Task management** - phase-grouped tasks from incident templates
- **Inbound webhook API** - create cases from ServiceDesk Plus, Jira, or anything that can POST JSON
- **Investigation graph** - visual relationship map between IOCs, timeline entries, and evidence
- **Self-hosted** - your incident data stays on your infrastructure

The core above is AGPL-3.0 and free forever. See [irdoc.io](https://irdoc.io) for details.

Full docs, quick start, and deployment guides: **[docs.irdoc.io](https://docs.irdoc.io)**

---

## Security

If you discover a security vulnerability, please report it to **security@irdoc.io** rather than opening a public issue.

We aim to release patches for critical vulnerabilities within 24 hours of confirmation. See the badges above for our automated scanning (CodeQL, secret scanning, dependency audits, and an [OpenSSF Scorecard](https://scorecard.dev/viewer/?uri=github.com/soc-irdoc/irdoc-app)).

---

## Contributing

Contributions are welcome. See the [contributing guide](https://docs.irdoc.io/contributing) before opening a PR.

- Bug reports and feature requests: [GitHub Issues](https://github.com/soc-irdoc/irdoc-app/issues)
- Security vulnerabilities: security@irdoc.io (do not open public issues)

---

## Sponsorship

IRDoc's core is free and will stay that way. If your organization relies on it and wants to support ongoing development, reach out via [irdoc.io](https://irdoc.io) - we don't have a formal sponsorship program set up yet, but we'd like to hear from you.

---

## License

**Core** (this repository): [AGPL-3.0](LICENSE)
