"""Atomic UTF-8 storage. Captures intentionally survive application/OS restarts."""
import json
import os
import tempfile
from pathlib import Path


def atomic_write(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def write_json(path, text, expected_type):
    if not isinstance(json.loads(text), expected_type):
        raise ValueError("Unexpected JSON data type")
    atomic_write(path, text.encode("utf-8"))


class HistoryWriter:
    """Commit only complete, valid transfers; interrupted transfers preserve disk data."""
    def __init__(self, path):
        self.path = path
        self.parts = None

    def append(self, chunk, first, last):
        if first:
            self.parts = []
        if self.parts is None:
            raise ValueError("History transfer has not started")
        self.parts.append(chunk)
        if last:
            parts, self.parts = self.parts, None
            write_json(self.path, "".join(parts), list)
