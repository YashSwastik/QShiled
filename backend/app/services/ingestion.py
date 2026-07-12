"""
Secure File Ingestion Service

Responsibilities:
  - Validate upload size and file extension
  - For ZIP: extract safely with path-traversal prevention
  - Enumerate files with allowed extensions
  - Return metadata; never execute any file
  - Always clean up temp directories

Security measures implemented:
  - Extension allowlist (no .exe, .sh, .bat, etc.)
  - ZIP-slip protection (all extracted paths verified inside target dir)
  - Absolute-path rejection in archive entries
  - Traversal component rejection (../)
  - Malformed ZIP rejection
  - Empty archive detection
  - Configurable max upload size
  - No sensitive content logging
  - Temp dir cleanup via context manager / explicit cleanup
"""
import os
import zipfile
import tempfile
import hashlib
import shutil
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import IO

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

# Phase 4 extensions supported by scanner (source code + certs + configs)
ALLOWED_EXTENSIONS: frozenset[str] = frozenset({
    ".py", ".js", ".ts", ".java", ".cs",
    ".json", ".yaml", ".yml", ".xml",
    ".properties", ".conf", ".config",
    ".pem", ".crt", ".cer",
})


@dataclass
class IngestionResult:
    """Returned after successful ingestion."""
    upload_name: str
    upload_type: str           # "zip" | "single_file"
    total_bytes: int
    supported_files: list[str] = field(default_factory=list)
    skipped_files: list[str] = field(default_factory=list)
    file_count: int = 0        # count of supported files discovered
    sha256: str = ""


class IngestionError(Exception):
    """Raised for safe, user-visible ingestion failures."""
    pass


def _sha256_of_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_allowed(filename: str) -> bool:
    ext = Path(filename).suffix.lower()
    return ext in ALLOWED_EXTENSIONS


def _safe_zip_extract(zf: zipfile.ZipFile, extract_dir: Path) -> tuple[list[str], list[str]]:
    """
    Extract ZIP safely.

    For every entry:
      - Reject absolute paths
      - Reject any path component that is '..'
      - Resolve final path and assert it's under extract_dir
      - Only extract if extension is allowed

    Returns (supported_file_paths, skipped_file_names)
    """
    supported: list[str] = []
    skipped: list[str] = []

    for info in zf.infolist():
        # Skip directories
        if info.filename.endswith("/"):
            continue

        # Reject absolute paths
        if os.path.isabs(info.filename):
            raise IngestionError(
                f"Archive contains absolute path entry — rejected: {info.filename!r}"
            )

        # Reject path traversal components
        parts = Path(info.filename).parts
        if any(part == ".." for part in parts):
            raise IngestionError(
                f"Archive contains path traversal entry — rejected: {info.filename!r}"
            )

        # Resolve final destination and assert it stays inside extract_dir
        dest = (extract_dir / info.filename).resolve()
        extract_resolved = extract_dir.resolve()
        try:
            dest.relative_to(extract_resolved)
        except ValueError:
            raise IngestionError(
                f"Archive entry escapes extraction directory — rejected: {info.filename!r}"
            )

        base_name = Path(info.filename).name
        if _is_allowed(base_name):
            zf.extract(info, extract_dir)
            supported.append(str(dest))
        else:
            skipped.append(info.filename)

    return supported, skipped


def ingest_upload(
    filename: str,
    file_obj: IO[bytes],
    max_bytes: int | None = None,
) -> IngestionResult:
    """
    Main ingestion entry point.  Reads file_obj completely, checks size,
    validates, and processes.  All temp files are cleaned up before returning.

    Args:
        filename: Original filename (used for type detection, sanitized here)
        file_obj: Readable binary stream
        max_bytes: Override for max size (defaults to settings value)

    Returns:
        IngestionResult with discovered file list and metadata

    Raises:
        IngestionError: for any user-visible problem
    """
    if max_bytes is None:
        max_bytes = settings.max_upload_size_bytes

    # Read fully into memory to check size (streams may not support seek)
    raw: bytes = file_obj.read()
    total_bytes = len(raw)

    if total_bytes == 0:
        raise IngestionError("Uploaded file is empty.")

    if total_bytes > max_bytes:
        mb = max_bytes / (1024 * 1024)
        raise IngestionError(f"Upload exceeds maximum size of {mb:.0f} MB.")

    # Sanitize filename — strip directories, keep only basename
    safe_name = Path(filename).name
    if not safe_name:
        raise IngestionError("Invalid filename.")

    sha = _sha256_of_bytes(raw)
    suffix = Path(safe_name).suffix.lower()

    tmp_dir: str | None = None
    try:
        if suffix == ".zip":
            return _process_zip(safe_name, raw, sha, total_bytes)
        elif _is_allowed(safe_name):
            return _process_single_file(safe_name, raw, sha, total_bytes)
        else:
            raise IngestionError(
                f"File type {suffix!r} is not supported. "
                f"Allowed: ZIP archives or individual source/config/cert files."
            )
    finally:
        # tmp_dir cleanup is handled inside each processor; nothing to do here
        pass


def _process_zip(
    safe_name: str,
    raw: bytes,
    sha: str,
    total_bytes: int,
) -> IngestionResult:
    """Safely extract and enumerate ZIP, clean up temp dir."""
    tmp_dir = tempfile.mkdtemp(prefix="qshield_ingest_")
    try:
        # Validate ZIP structure before extracting
        try:
            import io as _io
            zf = zipfile.ZipFile(_io.BytesIO(raw), "r")
        except zipfile.BadZipFile:
            raise IngestionError("The uploaded file is not a valid ZIP archive.")

        with zf:
            infolist = zf.infolist()
            # Count actual file entries (not directory entries)
            real_entries = [i for i in infolist if not i.filename.endswith("/")]
            if not real_entries:
                raise IngestionError("The ZIP archive is empty (contains no files).")

            extract_dir = Path(tmp_dir)
            supported, skipped = _safe_zip_extract(zf, extract_dir)

        return IngestionResult(
            upload_name=safe_name,
            upload_type="zip",
            total_bytes=total_bytes,
            supported_files=[str(Path(p).relative_to(tmp_dir)) for p in supported],
            skipped_files=skipped,
            file_count=len(supported),
            sha256=sha,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _process_single_file(
    safe_name: str,
    raw: bytes,
    sha: str,
    total_bytes: int,
) -> IngestionResult:
    """Accept a single allowed file; no disk write needed."""
    return IngestionResult(
        upload_name=safe_name,
        upload_type="single_file",
        total_bytes=total_bytes,
        supported_files=[safe_name],
        skipped_files=[],
        file_count=1,
        sha256=sha,
    )
