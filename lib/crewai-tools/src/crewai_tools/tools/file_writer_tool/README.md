# FileWriterTool Documentation

## Description

`FileWriterTool` writes text to a file. Missing directories are created automatically. The default encoding is UTF-8. The tool writes text only, not binary files.

Writes stay inside `base_dir`, which defaults to the current working directory.

## Installation

```shell
pip install 'crewai[tools]'
```

## Example

```python
from crewai_tools import FileWriterTool

file_writer_tool = FileWriterTool()

result = file_writer_tool.run(
    filename='example.txt',
    content='This is a test content.',
    directory='test_directory',
)
print(result)
```

## Arguments

The agent supplies these at runtime:

- `filename`: Name of the file to write, relative to `directory`. May include subdirectories, which are created if they do not exist.
- `content`: The text to write.
- `directory` (optional): Directory to write into. A relative path resolves inside the tool's allowed directory (`base_dir` when set, otherwise the current working directory) and defaults to that directory's root (`./`). Created if it does not exist.
- `overwrite` (optional): Whether to replace an existing file. Accepts `true`/`false` (also `yes`/`no`, `on`/`off`, `1`/`0`). Defaults to `false`, which reports an error instead of replacing the file.

You set these when constructing the tool:

- `base_dir` (optional): Directory that writes must stay inside. Defaults to the current working directory at write time. A path you set is resolved when the tool is constructed, so a later change of working directory does not move it.
- `encoding` (optional): Text encoding used to write the file. Defaults to `utf-8`.

## Allowed paths

Because `directory` and `filename` are usually chosen by an LLM at runtime, writes are confined to a sandbox:

- The resolved `directory` must be inside `base_dir` (the current working directory at write time if you do not set `base_dir`).
- The resolved file path must be inside that `directory`.
- `..` segments, absolute paths, and symlinks are resolved before both checks, so they cannot be used to escape.

To let an agent write outside the working directory, point `base_dir` at the target tree:

```python
file_writer_tool = FileWriterTool(base_dir='/var/output')
```

Previously, an absolute `directory` could write anywhere the process had permission. If you relied on that, set `base_dir` to the tree you want to allow. Setting `CREWAI_TOOLS_ALLOW_UNSAFE_PATHS=true` restores the old behavior, but it disables path and URL checks process-wide for every crewai-tools tool, including the SSRF protections on URL-fetching tools. Prefer `base_dir`. Managed workers should set `CREWAI_TOOLS_FORCE_SAFE_PATHS=true` so a tenant cannot disable those checks.
