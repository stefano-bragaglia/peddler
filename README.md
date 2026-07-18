# Peddler

![Peddler logo](docs/logo.png)

[![CI](https://github.com/stefano-bragaglia/peddler/actions/workflows/ci.yml/badge.svg)](https://github.com/stefano-bragaglia/peddler/actions/workflows/ci.yml)
[![Python 3.14+](https://img.shields.io/badge/python-3.14%2B-blue.svg)](https://www.python.org/downloads/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![License](https://img.shields.io/github/license/stefano-bragaglia/peddler)](LICENSE)

<!-- PyPI version + Python versions badges added by /publish once the first version ships -->

**Peddler** peddles your CV, door to door, one job application form at a time. It's a Claude Code slash command,
`/apply <cv.md> <jd.md> <url>`, backed by an MCP server that gives the LLM a single browser session to drive —
visible by default, so you can watch it work; pass `--headless` to run it out of sight.

## Background

Peddler follows a strict split of responsibilities: the **LLM is the orchestrator**, the MCP tools are **dumb
executors**. Deciding what a page is asking for, planning field values from the CV filtered through the job
description, and judging success versus another form step are all left to the LLM's own reasoning during the
conversation — none of it is hardcoded pattern-matching. The tools only know how to perform one browser action
and report back what happened, including any validation error the page surfaced.

## Core tools

| Tool | What it does |
|------|--------------|
| `open_session(url)` / `close_session()` | Launches/tears down the single browser session for one `/apply` attempt |
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
- **Fakes for unit tests, real Chromium for the adapter itself.** Every browser-*tool* test (`open_session`,
  `fill_field`, `advance_page`, ...) injects a fake page object so the bulk of the suite stays fast and
  browser-free. The real Playwright adapter that those fakes stand in for is exercised separately, against
  local HTML fixtures in a real (headless-forced) Chromium instance — it's the one place a fake can't catch a
  bug in the adapter's own Playwright calls (e.g. a page navigated to before its JS content had rendered).
- **`goto()` waits for `networkidle`, not just `load`.** Many real careers pages render their actual application
  form as a client-side "micro-app" well after the base HTML's `load` event fires; waiting only for `load`
  reliably captured an empty page shell. `networkidle` costs a little latency but is what makes `open_session`
  actually see the rendered form.
- **Field errors detected via a best-effort `aria-invalid`/`aria-describedby` heuristic.** `advance_page`'s
  real adapter has no way to know an arbitrary site's validation markup in advance, so after submitting it
  scans for `aria-invalid="true"` elements and reads their message from whatever `aria-describedby` points at.
  It won't catch a page that signals errors some other way, but costs nothing to add and catches the common
  case.
- **Visible by default, `--headless` to opt out.** Watching the browser act on a page is the fastest way to
  debug a stuck `/apply` run, so `peddler` launches Chromium visibly unless you pass `--headless`.
- **Passwords never reach the LLM.** `read_credentials` deliberately omits the password from its return value;
  `fill_credential_field` resolves and applies it server-side. The only code path a stored password travels
  through is one the LLM's context never sees.
- **`peddler` execs `claude` instead of spawning and babysitting it.** Claude Code already spawns the MCP server
  as its own child process and kills it on exit — that's how MCP over stdio works, not something `peddler` has
  to implement. Replacing its own process (`os.execvp`) means closing the terminal tears the whole chain down
  together via ordinary OS signal propagation, with no manual process-pairing code.

## Known limitations

By design, not by omission — explicitly out of scope for this version:

- No CAPTCHA solving or anti-bot/stealth evasion beyond normal, honest form-filling.
- No cover-letter generation.
- One active `/apply` session at a time; concurrent runs aren't supported. `peddler` makes running multiple
  simultaneous sessions easier to reach for, but neither `CredentialStore` nor `ApplicationLog` has file
  locking — for now, either apply to one job at a time or point simultaneous sessions at distinct
  `--credentials`/`--applog` paths.
- The credentials log book is stored in plaintext on disk — encryption at rest is deferred.
- Obfuscated emails in a CV (e.g. `name (at) domain (dot) com`) aren't recognized by the email extractor; only
  plain `user@domain.tld` forms are.

## Installation

Requires Python 3.14, [uv](https://docs.astral.sh/uv/), and Claude CLI.

```bash
uv tool install --editable .
uv run playwright install chromium
```

`uv tool install` (not `uv run`) matters here: it puts `peddler` and `peddler-mcp` on your `PATH` **globally**,
not just for the duration of one `uv run` invocation. `peddler-mcp` needs to be resolvable later, whenever Claude
Code spawns it — which may well be from a different terminal/shell session than the one you installed from.

## Usage

Start a session with the `peddler` launcher — it installs the `/apply` command for Claude Code (idempotent,
`~/.claude/commands/apply.md`), checks Playwright is ready, registers the MCP server with Claude Code (local
scope, also idempotent), and hands off to `claude` in the target workspace:

```
$ peddler --dir ~/job-search --credentials ~/job-search/.peddler/credentials.json
```

`--dir` defaults to the current directory; `--credentials`/`--applog` default to `~/.peddler/credentials.json`/
`~/.peddler/applications.log`. The browser session is visible by default (so you can watch `/apply` work);
pass `--headless` to run it out of sight. Anything after a `--` is forwarded to `claude` itself (e.g.
`-- --model opus`). Closing the terminal (or exiting Claude Code normally) ends the whole session, MCP server
included.

From inside that Claude Code session:

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
    │   ├── mcp/            ← stdio JSON-RPC transport, tool registry, server loop, peddler-mcp entry point
    │   ├── credentials/    ← credentials log book: storage, password generation, tools
    │   ├── applog/         ← persistent application log: storage, tools
    │   ├── browser/        ← Playwright session lifecycle, field fill, navigation, retry policy
    │   ├── commands/       ← the `/apply` slash command definition
    │   ├── launcher.py     ← the `peddler` console script
    │   └── email.py        ← CV contact-email extraction
    ├── scripts/            ← dev tooling (e.g. the per-file coverage check, below)
    └── tests/              ← 140 tests, 99%+ coverage

## Dev

```bash
uv run ruff check                                   # lint + docstring style (pydocstyle)
uv run radon cc -n B src tests                      # cyclomatic complexity report
uv run pytest --cov=src/peddler --cov-fail-under=90  # test suite with an aggregate coverage gate
uv run coverage json -o coverage.json -q && uv run python scripts/check_file_coverage.py  # per-file coverage gate
```

A pre-commit hook enforces all four gates on every commit; CI enforces them on every pull request.

## Contributing

Pull requests welcome. Please make sure the gates above pass before opening one.

## License

MIT
