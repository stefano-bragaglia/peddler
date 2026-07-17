# /apply <cv.md> <jd.md> <url>

Drive one job application attempt end to end: read a CV and a job description, open the target URL, handle
sign-up/login if needed, fill and submit the application form across as many steps as it takes, and record the
outcome.

## `$ARGUMENTS`

Three positional parts, in order:

1. `<cv.md>` — path to the applicant's CV, Markdown.
2. `<jd.md>` — path to the job description, Markdown.
3. `<url>` — the application form's starting URL.

Read `<cv.md>` and `<jd.md>` yourself (built-in file reading) before opening the session — no dedicated Peddler
tool is needed for that. If either path doesn't exist or isn't readable, stop and report the error; don't proceed
with an empty CV/JD. Refuse to start a second `/apply` if one is already active in this conversation (only one
active session at a time).

## Protocol

1. **Open the session.** Call `open_session(url)`. If it fails, treat it like any other tool failure per the
   retry policy below.

2. **Detect and handle a login/sign-up page**, before field analysis, if the opened page looks like one:
   - Find a contact email in the CV; if none is present, ask the user for one.
   - Call `read_credentials(site)`. If found, tell the user stored credentials are being reused, and log in using
     `fill_credential_field` for the password field — **never** use `read_credentials`'s returned data with
     `fill_field` to place a password on the page; `read_credentials` never even returns the password value, only
     `found`/`username`, and `fill_credential_field` looks it up and applies it server-side without the plaintext
     ever entering this conversation.
   - If no entry exists, tell the user a new account is about to be created with that email, generate a secure
     password, complete the sign-up, and call `write_credentials(site, username, password)` to store it. The
     generated password is **never** echoed into this conversation's output under any circumstance — it goes
     straight to the credentials log book via `write_credentials` and nowhere else.

3. **Loop over form pages** until the flow ends:
   - Identify the requested fields from the page content the tools return.
   - Plan each field's value from the CV, filtered/tailored through the JD.
   - Call `fill_field(field_id, value)` for each field (or `fill_credential_field` for a password field tied to
     the credentials log book).
   - If a field's fill or the subsequent `advance_page()` call reports a field-specific error, adjust that value
     and retry — this per-field correction loop is unbounded and separate from the tool-level retry described
     next; keep retrying field corrections as long as you're making progress.
   - Once the page's fields are filled with no outstanding errors, call `advance_page()`.
   - There is **no hard cap** on the number of form pages/steps traversed — keep going as long as the flow is
     making sense; use your own judgment (not a step counter) to recognize a flow that isn't converging, and
     treat that as Stuck Handling (below) rather than looping forever.

4. **Judge success vs. another step** from each `advance_page()` result:
   - Reads as a confirmation page → tell the user the application succeeded and to check their email for
     follow-ups from HR, call `close_session()`, call the application log's recording tool
     (`record_application(url, outcome)`) with `outcome="success"`, and stop.
   - Reads as another form step → go back to step 3 for the new page.

5. **Tool-failure retry policy** — auto-retry, not LLM guesswork: on a browser crash, timeout, or network drop
   specifically (as opposed to a validation error or other tool-reported problem), retry the failed tool call up
   to **3 attempts total with a short backoff** before giving up on it. This 3-attempt crash/timeout/network-drop
   policy is distinct from the unbounded, LLM-driven field-error correction loop in step 3 — don't conflate the
   two. If the retries are exhausted, treat it as Stuck Handling.

6. **Stuck Handling** — when something can't be resolved on your own (a CAPTCHA, an ambiguous field, an
   unresolvable validation error, or retries exhausted per step 5): pause and ask the user for guidance in this
   conversation. The browser stays **headless** during this pause — guidance is text-only; never attempt to solve
   a CAPTCHA yourself. If the user's guidance doesn't resolve it, abort: report the failure and its reason, call
   `close_session()`, call the recording tool with `outcome="stuck-unresolved"`, and suggest the user finish the
   application themselves by opening a normal, **visible** (non-headless) browser at the same URL — this
   post-abort fallback is the only point at which a visible browser window ever appears.

## Recording the outcome

Every attempt ends with exactly one call to the application log's recording tool, `record_application(url,
outcome)`, with `outcome` set to one of:

- `success`
- `aborted`
- `stuck-unresolved`
