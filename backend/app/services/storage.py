"""File storage on a local volume shared by the API and the worker."""

import os
import tempfile
from pathlib import Path


class LocalStorage:
    """Store files under a base directory, named by their content hash."""

    def __init__(self, base_dir: str | Path) -> None:
        """Create the storage.

        Args:
            base_dir: Directory where files are written (created if missing).
        """
        self._base = Path(base_dir)

    def save(self, content_hash: str, content: bytes) -> str:
        """Write a file atomically.

        The file is written to a temporary name and then renamed, so a reader
        never sees a half-written PDF.

        Args:
            content_hash: SHA-256 hex digest, used as the filename.
            content: File bytes.

        Returns:
            Absolute path of the stored file.
        """
        self._base.mkdir(parents=True, exist_ok=True)
        target = self._base / f"{content_hash}.pdf"
        if target.exists():
            return str(target)
        fd, tmp_path = tempfile.mkstemp(dir=self._base, suffix=".tmp")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
            os.replace(tmp_path, target)
        except BaseException:
            Path(tmp_path).unlink(missing_ok=True)
            raise
        return str(target)

    def path(self, stored_path: str) -> Path:
        """Resolve a stored path.

        Args:
            stored_path: Path returned by ``save``.

        Returns:
            The path as a ``Path`` object.
        """
        return Path(stored_path)
