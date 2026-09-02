from itertools import islice
import os
from typing import IO

from crewai.tools import BaseTool
from pydantic import BaseModel, Field, PrivateAttr, field_validator, model_validator
from typing_extensions import Self

from crewai_tools.security.safe_path import (
    format_error_for_display,
    format_path_for_display,
    format_sandbox_error,
    resolve_path,
    validate_file_path,
)


_DESCRIPTION = (
    "A tool that reads the content of a file. {default}Provide 'file_path' with "
    "the path to the file you want to read. Reads are confined to the tool's "
    "allowed directory; a path that resolves outside it is rejected. Optionally, "
    "provide 'start_line' to start reading from a specific line and 'line_count' "
    "to limit the number of lines read."
)


def _describe(default_label: str | None = None) -> str:
    default = (
        f"The default file is {default_label}, which is read when 'file_path' "
        f"is omitted. "
        if default_label is not None
        else ""
    )
    return _DESCRIPTION.format(default=default)


class FileReadToolSchema(BaseModel):
    """Input for FileReadTool."""

    file_path: str | None = Field(
        None,
        description=(
            "Full path of the file to read. Omit it to read the tool's default "
            "file, which only works when one was configured."
        ),
    )
    start_line: int | None = Field(
        1, description="Line number to start reading from (1-indexed)"
    )
    line_count: int | None = Field(
        None, description="Number of lines to read. If None, reads the entire file"
    )


class FileReadTool(BaseTool):
    """A tool for reading file contents.

    The file to read can be named in two ways:

    1. At construction time via ``file_path``, which becomes the tool's default.
    2. At runtime via the ``file_path`` argument in the tool's input.

    Paths supplied at runtime must resolve inside ``base_dir`` (the current
    working directory by default), since they are typically chosen by an LLM.
    A ``file_path`` given at construction time is developer-declared intent and
    is always allowed past the containment check, even when it lives outside
    ``base_dir`` (the read itself can still fail). It is pinned at
    construction, so a later chdir cannot repoint it, and it can be addressed
    either by omitting ``file_path`` or by the label shown in the description.

    Args:
        file_path: Path to the file to be read. If provided, this becomes the
            default file path for the tool.
        base_dir: Directory that runtime paths must stay inside. Defaults to
            the current working directory.
        encoding: Text encoding used to decode the file. Defaults to UTF-8.
        max_chars: Upper bound on the number of characters returned from a
            single read. Longer output is cut off with a note telling the
            agent to page through the file with ``start_line``/``line_count``.
            ``None`` (the default) returns the whole selection.

    Example:
        >>> tool = FileReadTool(file_path="/path/to/file.txt")
        >>> content = tool.run()  # Reads /path/to/file.txt
        >>> content = tool.run(file_path="/path/to/other.txt")  # Reads other.txt
        >>> content = tool.run(
        ...     file_path="/path/to/file.txt", start_line=100, line_count=50
        ... )  # Reads lines 100-149
        >>> # Widen the sandbox so the agent may read anything under /data:
        >>> tool = FileReadTool(base_dir="/data")
        >>> # Keep any single read under 20k characters:
        >>> tool = FileReadTool(max_chars=20_000)
    """

    name: str = "Read a file's content"
    description: str = _describe()
    args_schema: type[BaseModel] = FileReadToolSchema
    file_path: str | None = None
    base_dir: str | None = None
    encoding: str = "utf-8"
    max_chars: int | None = Field(default=None, gt=0)

    # Pinned at construction so a later chdir cannot change which file the
    # developer-declared default refers to.
    _declared_realpath: str | None = PrivateAttr(default=None)
    # The label the tool's description shows the LLM for the declared file.
    _declared_label: str | None = PrivateAttr(default=None)

    @field_validator("base_dir")
    @classmethod
    def _anchor_base_dir(cls, value: str | None) -> str | None:
        """Resolve base_dir once so a later chdir cannot move the sandbox."""
        return os.path.realpath(value) if value is not None else None

    @model_validator(mode="after")
    def _pin_declared_file(self) -> Self:
        """Pin the declared default file and advertise it in the description.

        Runs on ``model_validate`` too, so the pin survives a serialization
        round trip even though private attributes are not dumped.
        """
        if self.file_path is None:
            return self

        self._declared_realpath = resolve_path(self.file_path, self.base_dir)
        self._declared_label = format_path_for_display(self.file_path, self.base_dir)
        if "description" not in self.model_fields_set:
            self.description = _describe(self._declared_label)
        return self

    def _resolve_path(self, file_path: str) -> str:
        """Resolve *file_path* and confirm the tool is allowed to read it.

        The file declared at construction time is always allowed: the developer
        named it, and the tool reads it anyway when ``file_path`` is omitted. It
        is addressable both by its real path and by the label the description
        shows the LLM, since that label is all the model is given. Everything
        else — including any path an LLM invents at runtime — must resolve
        inside ``base_dir``.

        Raises:
            ValueError: If the path resolves outside ``base_dir``.
        """
        declared = self._declared_realpath
        if declared is not None and (
            file_path == self._declared_label
            or resolve_path(file_path, self.base_dir) == declared
        ):
            return declared
        return validate_file_path(file_path, self.base_dir)

    def _read_window(
        self, file: IO[str], start_line: int, line_count: int | None
    ) -> str | None:
        """Return the requested lines, or ``None`` if *start_line* is past EOF.

        A read cap only needs ``max_chars + 1`` characters to know whether to
        truncate, so a capped full read never pulls a huge file into memory.
        """
        if start_line == 1 and line_count is None:
            if self.max_chars is None:
                return file.read()
            return file.read(self.max_chars + 1)

        start_idx = max(start_line - 1, 0)
        stop_idx = None if line_count is None else start_idx + line_count

        # islice stops pulling lines once stop_idx is reached, so a small
        # window near the top of a huge file does not scan the whole file.
        selected_lines = list(islice(file, start_idx, stop_idx))
        if not selected_lines and start_idx > 0:
            return None
        return "".join(selected_lines)

    def _truncate(self, text: str, display_path: str) -> str:
        if self.max_chars is None or len(text) <= self.max_chars:
            return text
        return (
            f"{text[: self.max_chars]}\n\n[Output truncated to {self.max_chars} "
            f"characters. Use 'start_line' and 'line_count' to read the rest of "
            f"{display_path}.]"
        )

    def _run(
        self,
        file_path: str | None = None,
        start_line: int | None = 1,
        line_count: int | None = None,
    ) -> str:
        """Read a file, or a window of its lines, as text."""
        start_line = start_line or 1
        line_count = line_count or None

        if file_path is None:
            if self._declared_realpath is None:
                return "Error: No file path provided. Please provide a file path either in the constructor or as an argument."
            file_path = self._declared_realpath
        else:
            try:
                file_path = self._resolve_path(file_path)
            except ValueError as e:
                return "Error: Invalid file path: " + format_sandbox_error(
                    e,
                    "Pass base_dir to FileReadTool to allow reading another "
                    "directory tree.",
                )

        display_path = format_path_for_display(file_path, self.base_dir)
        try:
            with open(file_path, "r", encoding=self.encoding) as file:
                text = self._read_window(file, start_line, line_count)
        except FileNotFoundError:
            return f"Error: File not found at path: {display_path}"
        except PermissionError:
            return f"Error: Permission denied when trying to read file: {display_path}"
        except UnicodeDecodeError:
            return (
                f"Error: Failed to decode file {display_path} as {self.encoding}. "
                f"Pass a different 'encoding' to FileReadTool if the file uses "
                f"another text encoding."
            )
        except Exception as e:
            return (
                f"Error: Failed to read file {display_path}. "
                f"{format_error_for_display(e)}"
            )

        if text is None:
            return f"Error: Start line {start_line} exceeds the number of lines in the file."
        return self._truncate(text, display_path)
