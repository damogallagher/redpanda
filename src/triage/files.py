"""Private, atomic JSON reports; a failed replacement preserves the previous report."""

import json
import os
import tempfile
from pathlib import Path


def write_private_json(path: Path, value: object) -> None:
    # Encode before touching the filesystem. Reports can contain model transcripts.
    data = json.dumps(value, indent=2) + "\n"
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".triage-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        # Replace the directory entry, never follow an existing destination symlink.
        # mkstemp creates mode 0600 even when the replaced file was world-readable.
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
