# Agent Instructions for CrewAI OSS

CrewAI is a Python based framework for building AI agents and agentic systems.
Follow these guidelines when contributing:

## Key Guidelines

1. Follow Python best practices and idiomatic patterns.
2. Maintain existing code structure and organization.
3. Write unit tests for new functionality focusing on behaivor and not
   implementation.
4. Document public APIs and complex logic.
5. Suggest changes to the `docs/` folder when appropriate
6. Follow software principles such as DRY and YAGNI.
7. Keep diffs as minimal as possible.

## Message Content

`LLMMessage.content` is `str | list[dict[str, Any]] | None`; the list form is
multimodal content parts. Never `str()` it — that puts a Python repr
(`[{'type': 'text', 'text': 'hi'}]`) in front of the model and into memory.
Collapse a message to text with the helper instead:

```python
from crewai.utilities.agent_utils import message_content_text

text = message_content_text(msg)  # "" for None; joined text for a parts list
```

Parts arrive from a model and are typed `dict[str, Any]`, so a `text` key that
is not a string is possible. `_content_parts_text` skips those blocks rather
than raising, and names a list with no usable text `[multimodal content]`.

## Changing Docs

1. Edit MDX under `docs/edge/en/*` and reference it from `docs/docs.json` if
   needed.
2. Do not modify files under `docs/v*/`. Those are frozen release snapshots
   managed by devtools.
3. Do not delete or rename files under `docs/images/` as frozen snapshots
   may reference them.
4. If you want to preview your changes locally, use `cd docs && mintlify dev`.
   To check for broken links, run `cd docs && mintlify broken-links`.
5. After editing English docs, sync translations to `ar`, `ko`, and `pt-BR`
   before finishing the task. Follow [DOCS_TRANSLATIONS.md](DOCS_TRANSLATIONS.md).

## Cursor Cloud specific instructions

This is a Python library monorepo (Crews + Flows + CLI), not a web app. There is no long-running application server. Development is `uv sync`, then edit Python, then `uv run pytest` / `uv run ruff` / `uv run crewai`.

Standard install, lint, type-check, and test commands live in [`.github/CONTRIBUTING.md`](.github/CONTRIBUTING.md). Use `uv`, not pip.

**Non-obvious run notes:**

- `uv` is installed at `~/.local/bin`. New shells pick it up via `~/.bashrc`; if a command cannot find `uv`, prepend `$HOME/.local/bin` to `PATH`.
- Pytest `addopts` already include `-n auto` (xdist) and `--block-network`. Do not pass `-p no:xdist`; it conflicts with those addopts and pytest exits with an unrecognized-arguments error.
- The test suite is offline: `.env.test` supplies fake keys and VCR cassettes replay HTTP. A live `crewai run` against a real provider needs an LLM API key (for example `OPENAI_API_KEY`).
- `crewai create crew <name>` is interactive unless you set `CREWAI_DMN=1` (skips the provider picker).
- Docs preview is optional: `cd docs && mintlify dev`.
