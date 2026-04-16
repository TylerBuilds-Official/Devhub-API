"""
Efficient tail-N reader for log files.

NSSM-managed log files grow unbounded until rotated — could be hundreds
of MB. Slurping the whole file to grab the last 200 lines would be
wasteful, so this reads chunks backward from EOF until we have enough
newlines, then decodes only that slice.

Returns oldest → newest so callers can render straight into a log tail
without re-reversing.
"""
import logging
import os

from pathlib import Path


logger = logging.getLogger(__name__)

# 8KB per reverse-read chunk. Big enough to usually get the whole
# requested tail in one read for normal log lines, small enough to
# avoid over-reading for short tails.
_CHUNK_SIZE = 8_192


class LogFileMissingError(FileNotFoundError):
    """Raised when a configured log path doesn't exist on disk."""


class LogFileReadError(OSError):
    """Raised when a log file exists but can't be read (permissions, etc.)."""


def tail_file(path: str, n: int) -> list[str]:
    """
    Return the last `n` lines of the file at `path`, oldest-first.

    Raises LogFileMissingError if the path doesn't exist. Raises
    LogFileReadError for other I/O failures. An empty file returns [].
    """

    if n <= 0:
        return []

    p = Path(path)

    if not p.exists():
        raise LogFileMissingError(f"Log file not found: {path}")

    try:
        size = p.stat().st_size
    except OSError as e:
        raise LogFileReadError(f"Failed to stat {path}: {e}") from e

    if size == 0:
        return []

    # Reverse-read chunks until we have n+1 newlines (+1 because the
    # last newline is usually the trailing one at EOF).
    lines_needed = n + 1
    buffer       = b""
    pos          = size

    try:
        with p.open("rb") as f:
            while pos > 0 and buffer.count(b"\n") < lines_needed:
                read_size = min(_CHUNK_SIZE, pos)
                pos      -= read_size

                f.seek(pos)
                chunk  = f.read(read_size)
                buffer = chunk + buffer

    except OSError as e:
        raise LogFileReadError(f"Failed to read {path}: {e}") from e

    # Decode tolerantly — NSSM log output may contain mojibake if a
    # service writes raw bytes. Replacement chars are better than a 500.
    text = buffer.decode("utf-8", errors="replace")

    # Split, trim trailing empty line that comes from EOF newline.
    lines = text.splitlines()

    return lines[-n:]


def log_file_exists(path: str) -> bool:
    """Cheap check — useful for graceful UI when a path is misconfigured."""

    try:
        return os.path.isfile(path)
    except OSError:
        return False
