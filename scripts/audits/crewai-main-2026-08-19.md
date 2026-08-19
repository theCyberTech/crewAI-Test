# Dry-run audit: CrewAI OSS `main`

- **Repository:** this workspace (CrewAI OSS monorepo: Crews + Flows + CLI)
- **Branch / commit:** `main` @ `cdd919ae`
- **Date:** 2026-08-19
- **Mode:** dry run — findings only. No sweeping source refactors.
- **PR policy:** this run saves the checklist + report; it does **not** apply
  multi-file production fixes. Confirm before any of those land.

This is a Python library, not a web app. Checks that assume HTTP route
handlers or React components are recorded as **none found** when the analogue
does not exist, with the closest related finding noted.

Production scope: `lib/*/src` excluding tests and CLI templates.

---

## 1. Duplicate utility functions — proposed

Not counted: polymorphic overrides (`list_files` on uploaders, `kickoff_async`
on Crew/Flow/Agent) or one-line wrappers (`sanitize_function_name` →
`sanitize_tool_name`).

| File:line | Duplicate | Proposal |
|-----------|-----------|----------|
| `lib/cli/src/crewai_cli/plus_api.py:24` and `lib/crewai-core/src/crewai_core/plus_api.py:202` | `_make_multipart_request` copied into the CLI subclass so older `crewai-core` still works | Keep until the compatibility window closes, then delete the CLI copy |
| `lib/crewai-tools/src/crewai_tools/aws/s3/reader_tool.py:33-38` and `writer_tool.py:34-39` | Identical `boto3.client("s3", ...)` plus `_parse_s3_path` | Shared `get_s3_client()` + `_parse_s3_path` helper |
| `lib/crewai/src/crewai/utilities/agent_utils.py:1602` (`execute_single_native_tool_call`) vs `lib/crewai/src/crewai/experimental/agent_executor.py:1913` (`_execute_single_native_tool_call`) | Native tool-call lifecycle implemented twice | Experimental executor should call the shared helper |
| `lib/crewai-tools/src/crewai_tools/rag/core.py:55-59` vs `lib/crewai/src/crewai/rag/chromadb/factory.py:12-34` | Two ChromaDB client construction paths | Tools RAG should use the framework factory |

## 2. Secrets committed in config files — none found

- `.gitignore` already ignores `.env` (line 5) and `secrets/*` (line 32).
- `.env.test` only contains `fake-*` placeholders (e.g. `OPENAI_API_KEY=fake-api-key` at line 12).
- No `sk-` / `AKIA` / `ghp_` live tokens in config or source.

## 3. Functions over 400 lines — proposed

Do not split these without a dedicated review; they are high-churn.

| Lines | File:line | Function |
|------:|-----------|----------|
| 835 | `lib/crewai/src/crewai/events/event_listener.py:168` | `setup_listeners` |
| 823 | `lib/cli/src/crewai_cli/crew_run_tui.py:2006` | `_subscribe` |
| 590 | `lib/crewai-tools/src/crewai_tools/tools/databricks_query_tool/databricks_query_tool.py:209` | `_run` |
| 431 | `lib/crewai/src/crewai/flow/runtime/__init__.py:2071` | `kickoff_async` |
| 411 | `lib/crewai/src/crewai/a2a/updates/streaming/handler.py:236` | `execute` |

Proposal: extract per-event handlers from `setup_listeners` / `_subscribe`;
split Databricks `_run` into connect / execute / format.

## 4. Components over 200 lines — proposed

No `.tsx`/`.jsx`/`.vue` components in this repo. Closest analogue is Textual TUI
apps/classes.

| Lines | File:line | Class |
|------:|-----------|-------|
| 2499 | `lib/cli/src/crewai_cli/crew_run_tui.py:330` | `CrewRunApp` |
| 590 | `lib/cli/src/crewai_cli/checkpoint_tui.py:132` | `CheckpointTUI` |
| 364 | `lib/cli/src/crewai_cli/memory_tui.py:30` | `MemoryTUI` |

Proposal: split `CrewRunApp` into run-state, event-subscription, and render
mixins. Leave core domain classes (`Crew`, `Flow`, `LLM`) out of this check;
they are not UI components.

## 5. Dead code — proposed

| File:line | Finding | Proposal |
|-----------|---------|----------|
| `lib/crewai/src/crewai/process.py:11` | `# TODO: consensual = 'consensual'` never implemented | Delete the comment or schedule the process type |
| `lib/crewai/src/crewai/experimental/agent_executor.py:1913` | Duplicate of the shared native tool-call helper (see check 1) | Delegate instead of keeping a second copy |
| `lib/cli/src/crewai_cli/plus_api.py:16-22` | Comment admits ZIP helpers are duplicated “so editable CLI installs still work” | Track a removal ticket once min `crewai-core` is new enough |

No unreferenced Python modules jumped out of the production packages; a full
vulture pass was not run.

## 6. Silent or empty catch blocks — proposed

AST scan of production `src`: **155** `except` bodies that are `pass` / `...` /
continue-only / bare `return`, **0** bare `except:`.

Highest-signal examples (swallow `Exception` with no log):

| File:line | Type | Proposal |
|-----------|------|----------|
| `lib/crewai/src/crewai/crew.py:2002` | `Exception` + `pass` (`# noqa: S110`) | Keep, but log at debug so hook failures are visible |
| `lib/crewai/src/crewai/agents/planner_observer.py:324,333,339` | `Exception` + `pass` | Log observer failures |
| `lib/crewai/src/crewai/events/listeners/tracing/utils.py` (many, e.g. 200, 222, 248, 255, 263, 268, 274, 304, 314, 330, 337, 346, 352) | `Exception` + `pass`/`continue` | One debug log at the helper that already sanitizes trace payloads |
| `lib/cli/src/crewai_cli/crew_run_tui.py` (many, e.g. 74, 308, 788, 854, 951, 979, 1115, 1477, 1955) | `Exception` + `pass`/`return` | Log at debug; TUI must not crash, but operators need a trace |
| `lib/crewai-tools/src/crewai_tools/tools/snowflake_search_tool/snowflake_search_tool.py:275,279,287` | `Exception` + `pass` | Return/log the Snowflake error |
| `lib/crewai-core/src/crewai_core/telemetry.py:105` | `Exception` + `pass` | Acceptable for telemetry opt-out; add debug log |

Do **not** add logging to all 155 in one PR. Start with `Exception` + `pass`
in crew/planner/tracing/TUI.

## 7. API calls in the UI missing loading/error states — proposed

No web UI. TUI coverage is mostly good (`memory_tui.py:352` sets
`panel.loading`; `crew_run_tui.py` tracks `_error` at 544 and renders it at
1334+). Gap:

| File:line | Finding | Proposal |
|-----------|---------|----------|
| `lib/cli/src/crewai_cli/deploy/main.py:569-574` | `list_crews` calls `response.json()` **before** the status check, then on non-200 prints “You don't have any Crews yet” instead of the API error | Parse JSON after `is_success`; reuse `PlusAPIMixin._validate_response` (as `triggers/main.py:27-28` already does) |

`remote_template/main.py:45-49` handles empty lists; `_fetch_templates` at
165-170 already shows a red error on HTTP failure.

## 8. Database queries written directly in route handlers — none found

This repo has no FastAPI/Flask/Django route handlers. SQLite lives in
persistence classes (`flow/persistence/sqlite.py`,
`state/provider/sqlite_provider.py`,
`memory/storage/kickoff_task_outputs_storage.py`), which is the right layer.

Related (filed under check 16, not here):
`kickoff_task_outputs_storage.py:147` interpolates column names into SQL.

## 9. Synchronous I/O in request handlers — none found

No async HTTP server request handlers in this OSS tree. A2A streaming is
async (`httpx.AsyncClient`). `PlusAPI._make_request`
(`plus_api.py:181-200`) is a **client** that uses sync `httpx.Client` per
call — expected for CLI. Not a server handler.

## 10. List endpoints with no pagination — proposed

In-repo HTTP **server** list routes: none found.

Client/list APIs that return unbounded collections:

| File:line | Method | Proposal |
|-----------|--------|----------|
| `lib/crewai-core/src/crewai_core/plus_api.py:313` | `list_skills` — optional `org`, no page/limit | Add `page`/`limit` query params when the Plus API supports them |
| `lib/crewai-core/src/crewai_core/plus_api.py:359` | `list_crews` — no pagination | Same |
| `lib/crewai-core/src/crewai_core/plus_api.py:502` | `get_triggers` | Same |
| `lib/crewai-files/src/crewai_files/uploaders/openai.py:444` | `list_files` uses `client.files.list()` first page only | Paginate `files.data` / auto-iterate |
| `lib/crewai/src/crewai/mcp/client.py:374` | `list_tools` returns the full MCP list | Honor MCP `nextCursor` if the server sends it |

Already paginated (not findings): `StorageBackend.list_records`
(`memory/storage/backend.py:117`, default `limit=200`); A2A `list_tasks`
(`a2a/utils/task.py:506`, `page_size=50`); GitHub template fetch
(`remote_template/main.py:160-182`, `per_page=100`).

## 11. Inconsistent API response shapes — proposed

`PlusAPI` always returns raw `httpx.Response` (consistent at the client).
Callers disagree:

| File:line | Shape assumed | Proposal |
|-----------|---------------|----------|
| `lib/cli/src/crewai_cli/deploy/main.py:576` | success body is a **list** of crews | Typed client methods returning `{data, error}` |
| `lib/cli/src/crewai_cli/deploy/main.py:545-556` | create success is a **dict** with `uuid`/`status` | Same envelope |
| `lib/cli/src/crewai_cli/command.py:59-68` | 422 body is `{field: [messages]}` | Document this as the error envelope |

No in-repo HTTP handlers to unify. Proposal is on the Plus client + CLI
parsers only.

## 12. Floats used for money instead of integer cents — proposed

This product does not store currency. The only money-like field is LLM cost:

| File:line | Finding | Proposal |
|-----------|---------|----------|
| `lib/crewai/src/crewai/llm.py:370` | `completion_cost: float \| None` | If this is ever billed or summed, store integer micros (or millicents) instead of IEEE floats. Token **counts** in `UsageMetrics` are already ints — leave those |

`TokenProcess` (`base_token_process.py:11-15`) tracks tokens as `int` only.

## 13. Dates stored as plain strings instead of ISO 8601 — proposed

Good: flow persistence writes `datetime.now(timezone.utc).isoformat()`
(`flow/persistence/sqlite.py:141`).

Not ISO 8601 (missing `T` and/or timezone):

| File:line | Format | Proposal |
|-----------|--------|----------|
| `lib/crewai/src/crewai/state/provider/sqlite_provider.py:44` | `%Y%m%dT%H%M%S` stored in `created_at TEXT` (line 19) | Store UTC ISO 8601 (`...Z`); keep compact form only in the checkpoint **id** |
| `lib/crewai/src/crewai/state/provider/json_provider.py:163` | same compact stamp in filenames | Fine for filenames; document it |
| `lib/crewai/src/crewai/utilities/logger.py:26` | `%Y-%m-%d %H:%M:%S` local naive | Display-only; optional ISO |
| `lib/crewai/src/crewai/utilities/file_handler.py:89` | same, persisted in JSON logs | Persist `isoformat()` UTC |
| SQLite `DATETIME` columns (`kickoff_task_outputs_storage.py:55`, `flow/persistence/sqlite.py:84`) | SQLite affinity, not a typed timestamp | Keep ISO text (flow path already does) |

## 14. External calls with no retry/backoff — proposed

Retry **does** exist for LanceDB commits
(`lancedb_storage.py:34-39`, `_MAX_RETRIES = 5`) and MCP
(`mcp/client.py:395` `_retry_operation`).

No retry/backoff:

| File:line | Call | Proposal |
|-----------|------|----------|
| `lib/crewai-core/src/crewai_core/plus_api.py:199` | `client.request(...)` every Plus call | httpx transport retries on 429/5xx with cap |
| `lib/crewai/src/crewai/skills/registry.py:365` | `httpx.get(download_url)` | Retry transient failures |
| `lib/cli/src/crewai_cli/skills/main.py:133` | `httpx.get(download_url)` | Same |
| `lib/crewai-core/src/crewai_core/auth/oauth2.py:109,139` | `httpx.post` token exchange | Retry 5xx only |
| `lib/cli/src/crewai_cli/enterprise/main.py:50` | `httpx.get(oauth_endpoint)` | Same |
| `lib/cli/src/crewai_cli/remote_template/main.py:166,210` | GitHub `httpx.get` | Retry 429 |
| `lib/crewai-files/src/crewai_files/core/sources.py:533` | `httpx.get(self.url)` | Retry transient |
| `lib/devtools/src/crewai_devtools/docs_check.py:167` | `OpenAI()` with no retry wrapper | Optional |

Do not add unbounded retries. Cap at 2–3 attempts with exponential backoff.

## 15. Stale comments that no longer match the code — proposed

| File:line | Comment vs code | Proposal |
|-----------|-----------------|----------|
| `lib/crewai/src/crewai/llm.py:2353` | `# TODO: Remove this code after merging PR https://github.com/BerriAI/litellm/pull/10917` — LiteLLM workaround still in tree | Confirm whether that LiteLLM PR shipped; delete the TODO or the workaround |
| `lib/crewai/src/crewai/rag/chromadb/factory.py:22` | “Need to update to use chromadb.Client to support more client types in the near future” while the function already builds `PersistentClient` | Rewrite to describe current factory intent |
| `lib/crewai/src/crewai/knowledge/source/base_file_knowledge_source.py:19` | `file_path` field marked `[Deprecated]` | Confirm docs/changelog; if still accepted, keep; if ignored, remove the field |
| `lib/crewai/src/crewai/process.py:11` | TODO for a process type that does not exist | See check 5 |

Safe, local comment edits — still ask before a repo-wide comment sweep.

## 16. Unvalidated user input — proposed

YAML loaders correctly use `yaml.safe_load` (e.g. `crew_base.py:392`,
`skills/parser.py:64`). Findings:

| File:line | Issue | Proposal |
|-----------|-------|----------|
| `lib/crewai/src/crewai/utilities/file_handler.py:166` | `pickle.load` (`# noqa: S301`) | Prefer JSON; if pickle stays, only load files this process wrote |
| `lib/crewai/src/crewai/memory/storage/kickoff_task_outputs_storage.py:147` | `UPDATE ... SET {key} = ?` interpolates kwargs keys (`# noqa: S608`) | Allowlist columns (`task_id`, `expected_output`, `output`, `was_replayed`, `inputs`) |
| `lib/crewai-tools/src/crewai_tools/aws/s3/reader_tool.py:48-49` (same in `writer_tool.py:49-50`) | `_parse_s3_path` splits once and indexes `[1]` with no check | Reject paths that are not `s3://bucket/key` |
| `lib/crewai-tools/src/crewai_tools/tools/dalle_tool/dalle_tool.py:54` | `kwargs.get("image_description")` then used as prompt | Already returns if missing; schema-require the field |

## 17. API routes missing auth checks — none found (client caveat)

No HTTP API routes ship in this OSS repo (enterprise OpenAPI under `docs/`
is a published spec, not this server). CLI Plus commands go through
`PlusAPIMixin` (`command.py:26-38`), which **requires** `get_auth_token()`.

Caveat, not a missing route: `PlusAPI.__init__`
(`plus_api.py:167-168`) only sets `Authorization` when `api_key` is truthy, so
framework code that constructs `PlusAPI()` without a key can still call
`_make_request`. Proposal if that path is used in production: fail closed
when `api_key` is missing except for explicitly public endpoints.

## 18. Missing indexes on frequently queried columns — proposed

| File:line | Query pattern | Index present? | Proposal |
|-----------|---------------|----------------|----------|
| `lib/crewai/src/crewai/flow/persistence/sqlite.py:91,109` | `flow_uuid` / pending feedback uuid | Yes (`idx_flow_states_uuid`, `idx_pending_feedback_uuid`) | None |
| `lib/crewai/src/crewai/state/provider/sqlite_provider.py:31-34` | `DELETE ... WHERE branch = ?` prune | No index on `branch` | `CREATE INDEX IF NOT EXISTS idx_checkpoints_branch ON checkpoints(branch)` |
| `lib/crewai/src/crewai/memory/storage/kickoff_task_outputs_storage.py:147` | `WHERE task_index = ?` | PK is `task_id` only (line 49) | Index `task_index` |

## 19. N+1 queries — proposed

No ORM. Closest patterns:

| File:line | Pattern | Proposal |
|-----------|---------|----------|
| `lib/crewai/src/crewai/utilities/task_output_storage_handler.py:39-56` | `update()` **loads every row** then writes one | `UPDATE` by `task_index` without `load()`; `load()` is `SELECT *` at `kickoff_task_outputs_storage.py:176` |
| Replay loop `crew.py:2005-2017` | each finished task stores via handler | Fine if `add()` is a single INSERT; avoid `update()`’s full-table read |

LanceDB/Chroma searches take a `limit`; not N+1.

## 20. Third-party SDKs initialized in more than one place — proposed

| SDK | Sites | Proposal |
|-----|-------|----------|
| `boto3.client("s3")` | `crewai_tools/.../s3/reader_tool.py:33`, `writer_tool.py:34`, `crewai_files/uploaders/bedrock.py:165`; Bedrock runtime also in `llms/providers/bedrock/completion.py:2174` | Shared AWS session/client factory per process |
| `OpenAI()` / `AsyncOpenAI()` | `llms/providers/openai/completion.py:305,312`, `crewai_files/uploaders/openai.py:170,184`, `dalle_tool.py:52`, `ai_mind_tool.py:86`, `db2_search_tool.py:219`, `devtools/cli.py:1018`, `devtools/docs_check.py:167` | Tools should reuse `OpenAICompletion._get_sync_client()` or a tiny `get_openai_client()` |
| `Anthropic()` | `llms/providers/anthropic/completion.py:271`, `crewai_files/uploaders/anthropic.py:54` | File uploader already accepts an injected client — prefer that |
| ChromaDB | `rag/chromadb/factory.py:29` `PersistentClient` vs `crewai_tools/rag/core.py:55-59` `PersistentClient`/`Client` | Single factory (check 1) |

Provider completion classes constructing their own SDK once per LLM instance
is acceptable. Repeat **ad hoc** `OpenAI()` inside `_run` (DALL·E tool) is the
bug: a new client per invocation.

---

## Summary

| # | Check | Status |
|---|-------|--------|
| 1 | Duplicate utility functions | proposed |
| 2 | Secrets committed in config files | none found |
| 3 | Functions over 400 lines | proposed |
| 4 | Components over 200 lines | proposed |
| 5 | Dead code | proposed |
| 6 | Silent or empty catch blocks | proposed |
| 7 | API calls in the UI missing loading/error states | proposed |
| 8 | Database queries written directly in route handlers | none found |
| 9 | Synchronous I/O in request handlers | none found |
| 10 | List endpoints with no pagination | proposed |
| 11 | Inconsistent API response shapes | proposed |
| 12 | Floats used for money instead of integer cents | proposed |
| 13 | Dates stored as plain strings instead of ISO 8601 | proposed |
| 14 | External calls with no retry/backoff | proposed |
| 15 | Stale comments that no longer match the code | proposed |
| 16 | Unvalidated user input | proposed |
| 17 | API routes missing auth checks | none found |
| 18 | Missing indexes on frequently queried columns | proposed |
| 19 | N+1 queries | proposed |
| 20 | Third-party SDKs initialized in more than one place | proposed |

| Status | Count |
|--------|------:|
| fixed | 0 |
| proposed | 16 |
| none found | 4 |

Highest-leverage follow-ups (still ask before multi-file work):

1. Allowlist SQL columns in kickoff task-output `UPDATE`.
2. Fix `DeployCommand.list_crews` error handling.
3. Shared S3 client + path parser.
4. Index `checkpoints(branch)` and `latest_kickoff_task_outputs(task_index)`.
5. Plus API client retries + pagination params.
