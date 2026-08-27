# FileWriterTool Documentation

## Description

`FileWriterTool` writes text to a file.

It creates missing folders.
It uses UTF-8 by default.
It writes text only. It does not write binary files.

Writes stay inside a safe folder. By default, that folder is the current working directory. Pass `base_dir` to use a different folder.

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

The agent passes these when it runs:

- `filename`: File name, relative to `directory`. You can include folders in the name, like `reports/weekly.txt`. Missing folders are created.
- `content`: The text to write.
- `directory` (optional): Folder to write into. A relative path is inside the tool's allowed folder (`base_dir` if you set it, otherwise the current working directory). The default is that folder's root (`./`). Missing folders are created.
- `overwrite` (optional): Replace the file if it already exists. Pass `true` or `false`. Other yes/no spellings also work (`yes`/`no`, `on`/`off`, `1`/`0`). The default is `false`. If the file exists and `overwrite` is `false`, the tool returns an error and does not change the file.

You set these when you create the tool:

- `base_dir` (optional): The folder writes must stay inside. The default is the current working directory at write time. If you set a path, the tool locks it when you create the tool. Changing the working directory later does not move it.
- `encoding` (optional): How to encode the text. The default is `utf-8`.

## Allowed paths

An agent often chooses `directory` and `filename` at run time. The tool blocks paths that leave the safe folder.

- The final `directory` must be inside `base_dir`. If you do not set `base_dir`, that is the current working directory at write time.
- The final file path must be inside that `directory`.
- The tool resolves `..`, absolute paths, and symlinks before it checks. They cannot be used to leave the safe folder.

To let an agent write under a different folder, set `base_dir`:

```python
file_writer_tool = FileWriterTool(base_dir='/var/output')
```

Older versions let an absolute `directory` write anywhere the process could write. If you need that, set `base_dir` to the folder you want to allow.

`CREWAI_TOOLS_ALLOW_UNSAFE_PATHS=true` turns off these checks for every crewai-tools tool in the process. That also turns off URL safety checks. Prefer `base_dir`. On shared workers, set `CREWAI_TOOLS_FORCE_SAFE_PATHS=true` so a user cannot turn the checks off.
