# 20-Point Code Quality Audit Checklist

Reusable SOP for auditing a repository. Run the checks **in order**. Never skip a
check: if a category does not apply to the repo (for example a Python library
with no React UI), record **none found** and say why.

## Before you start — ask, then dry-run, then save

Do **not** start searching until the operator answers:

1. **Which repository and branch** should this run against?
2. **May this open pull requests directly**, or must it hand back a diff for
   review first?

Then:

3. **Dry-run** against the pointed-to repo/branch (findings only; no sweeping
   edits).
4. **Save** the reusable checklist (this file) plus the dated findings report.

Always **ask before any sweeping change that touches many files**. Apply a fix
during the audit only when it is local, clearly correct, and does not require
a cross-cutting refactor.

## Scope

Default production scope: application/library source. Exclude tests, generated
snapshots, vendor lockfiles, and frozen docs unless a check is specifically
about those files (for example committed secrets).

## The 20 checks (fixed order)

| # | Check | How to search | Fix vs propose |
|---|-------|---------------|----------------|
| 1 | Duplicate utility functions | Same helper name/body across modules that is not polymorphism or a thin wrapper | Propose a shared helper; do not merge without review |
| 2 | Secrets committed in config files | `api_key`/`password`/`token` literals, `sk-`/`AKIA`/`ghp_` patterns, `.env` not gitignored | Rotate if real; never commit live keys. Fake test keys are not findings |
| 3 | Functions over 400 lines | AST line span of `FunctionDef` / `AsyncFunctionDef` | Propose extract-method; do not split without review |
| 4 | Components over 200 lines | UI files (tsx/jsx/vue) or TUI/widget classes if there is no web UI | Propose split; do not split without review |
| 5 | Dead code | Unused exports, unfinished TODOs that landed as dead flags, duplicate implementations that the live path no longer uses | Propose deletion after confirming callers |
| 6 | Silent or empty catch blocks | AST `except` with `pass` / `...` / bare `return` / continue-only and no log or re-raise | Propose log-or-raise; skip intentional `# noqa: S110` only if commented |
| 7 | API calls in the UI missing loading/error states | fetch/axios/httpx from UI/TUI/CLI display paths | Propose loading + error; do not rewrite UI without review |
| 8 | Database queries written directly in route handlers | SQL/`execute` inside FastAPI/Flask/Django views | Propose a repository layer |
| 9 | Synchronous I/O in request handlers | `open()`, `time.sleep`, sync `httpx`/`requests` inside async HTTP handlers | Propose async or thread offload |
| 10 | List endpoints with no pagination | `list_*` HTTP/client methods with no `limit`/`offset`/`cursor`/`page` | Propose pagination params |
| 11 | Inconsistent API response shapes | Some handlers return raw lists, others `{data}`, others `{error}` | Propose a single envelope |
| 12 | Floats used for money instead of integer cents | `price`/`cost`/`amount` as `float` | Propose integer minor units |
| 13 | Dates stored as plain strings instead of ISO 8601 | `strftime` into SQLite/JSON without `isoformat()` / timezone | Propose UTC ISO 8601 |
| 14 | External calls with no retry/backoff | `httpx`/`requests` without retry/tenacity | Propose bounded retry on 429/5xx |
| 15 | Stale comments that no longer match the code | TODOs citing merged PRs, comments describing old control flow | Propose comment fix (safe to apply locally) |
| 16 | Unvalidated user input | `pickle.load`, `yaml.load` (unsafe), SQL string interpolation, path traversal | Propose allowlists / parameterized queries |
| 17 | API routes missing auth checks | HTTP routes without auth dependency; clients that send unauthenticated by default | Propose required auth |
| 18 | Missing indexes on frequently queried columns | `WHERE`/`ORDER BY`/`JOIN` columns vs `CREATE INDEX` | Propose migration; do not add indexes without review |
| 19 | N+1 queries | Loop that `load`/`get`/`execute` per item | Propose batch/join |
| 20 | Third-party SDKs initialized in more than one place | `OpenAI()`, `boto3.client()`, `chromadb.*Client()` constructed ad hoc | Propose a shared factory |

## Report format

For each check:

- **Status:** `fixed` | `proposed` | `none found`
- **Findings:** file + line for every hit (or a representative set plus a count
  when a pattern repeats dozens of times)
- **Action:** the proposed or applied fix

End with a 20-row summary table. Never omit a check.
