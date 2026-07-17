# Peddler

![Peddler logo](docs/logo.png)

[![CI](https://github.com/stefano-bragaglia/peddler/actions/workflows/ci.yml/badge.svg)](https://github.com/stefano-bragaglia/peddler/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/stefano-bragaglia/peddler)](LICENSE)

<!-- PyPI version + Python versions badges added by /publish once the first version ships -->

**Peddler** peddles your CV, door to door, one job application form at a time. It's a Claude Code slash command,
`/apply <cv.md> <jd.md> <url>`, backed by an MCP server that gives the LLM a single headless browser session to
drive.

## Background

Peddler follows a strict split of responsibilities: the **LLM is the orchestrator**, the MCP tools are **dumb
executors**. Deciding what a page is asking for, planning field values from the CV filtered through the job
description, and judging success versus another form step are all left to the LLM's own reasoning during the
conversation — none of it is hardcoded pattern-matching. The tools only know how to perform one browser action
and report back what happened, including any validation error the page surfaced.

## Core tools

| Tool | What it does |
|------|--------------|
| `open_session(url)` / `close_session()` | Launches/tears down the single headless browser session for one `/apply` attempt |
| `fill_field(field_id, value)` | Sets a form field's value; reports success or the page's own validation error |
| `fill_credential_field(field_id, site)` | Same, but the value is a stored password resolved server-side — it never enters the LLM's context or this conversation |
| `advance_page()` | Submits/advances the current page; retried with backoff on a crash, timeout, or network drop |
| `read_credentials(site)` / `write_credentials(site, username, password)` | The only way anything touches the local credentials log book |
| `record_application(url, outcome)` / `list_applications(url=None)` | Append-only application history: outcome is `success`, `aborted`, or `stuck-unresolved` |

## Design rationale

- **Single global session, not a session registry.** `open_session`/`close_session` hold one module-level
  session object rather than a session-id-keyed registry. One active `/apply` at a time is a hard requirement,
  not just today's use case, so a multi-session registry would be generality the system will never exercise.
- **`retry_with_backoff` as its own module.** Both `open_session`'s navigation and `advance_page`'s submit wrap
  the same generic, injectable-sleep retry helper rather than each hand-rolling a loop — the reliability policy
  (3 attempts, exponential backoff) is defined once and unit-tested once, not duplicated per call site.
- **Fakes over a real browser in tests.** Every browser-tool test injects a fake page object (or a fake
  `browser_factory`) instead of driving real Playwright. The full suite runs in well under a second with no
  browser binaries required in CI — the tradeoff is that the real Playwright adapter itself is a thin,
  intentionally-untested wrapper around a few one-line calls.
- **Passwords never reach the LLM.** `read_credentials` deliberately omits the password from its return value;
  `fill_credential_field` resolves and applies it server-side. The only code path a stored password travels
  through is one the LLM's context never sees.

## Known limitations

By design, not by omission — explicitly out of scope for this version:

- No CAPTCHA solving or anti-bot/stealth evasion beyond normal, honest form-filling.
- No cover-letter generation.
- One active `/apply` session at a time; concurrent runs aren't supported.
- The credentials log book is stored in plaintext on disk — encryption at rest is deferred.
- Obfuscated emails in a CV (e.g. `name (at) domain (dot) com`) aren't recognized by the email extractor; only
  plain `user@domain.tld` forms are.

## Installation

Requires Python 3.14, [uv](https://docs.astral.sh/uv/), and Claude CLI.

```bash
uv sync
uv run playwright install chromium
```

## Usage

From Claude CLI:

```
> /apply ~/cv.md ~/jobs/acme-backend-swe/jd.md https://acme.example.com/careers/apply/1234

Peddler: Reading job description and your CV...
Peddler: Opening https://acme.example.com/careers/apply/1234 ...
Peddler: This looks like a sign-up page. No stored credentials found for acme.example.com.
         I'll create an account using <email from CV>. A secure password has been generated
         and saved to the credentials log book (not shown here).
Peddler: Signed up, now on the application form (step 1 of 3).
Peddler: Filling: Full name, Email, Phone, Years of experience, Cover letter summary...
Peddler: Step 1 submitted. Now on step 2 of 3 (skills & experience)...
...
Peddler: Step 3 submitted. This page reads as a success confirmation:
         "Thank you for applying to Acme Corp!"
Peddler: 🎉 Application submitted successfully. Check your email for follow-ups from HR.
```

## Project layout

    peddler/
    ├── src/peddler/
    │   ├── mcp/            ← stdio JSON-RPC transport, tool registry, server loop
    │   ├── credentials/    ← credentials log book: storage, password generation, tools
    │   ├── applog/         ← persistent application log: storage, tools
    │   ├── browser/        ← Playwright session lifecycle, field fill, navigation, retry policy
    │   ├── commands/       ← the `/apply` slash command definition
    │   └── email.py        ← CV contact-email extraction
    └── tests/              ← 105 tests, 95%+ coverage

## Dev

```bash
uv run ruff check                                   # lint + docstring style (pydocstyle)
uv run radon cc -n B src tests                      # cyclomatic complexity report
uv run pytest --cov=src/peddler --cov-fail-under=90  # test suite with coverage gate
```

A pre-commit hook enforces all three gates on every commit; CI enforces them on every pull request.

## Contributing

Pull requests welcome. Please make sure the gates above pass before opening one.

## License

MIT
