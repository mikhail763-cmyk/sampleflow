"""Database utilities for SampleFlow.

Provides a simple SQLite helper that ensures the database runs in WAL
mode and creates the `samples` table on first initialization.

Usage:
    from app.core import database
    database.init_db()  # creates file at project root/sampleflow.db by default
    with database.get_connection() as conn:
        # use conn (sqlite3.Connection)

All functions are deliberately lightweight and use the standard library
`sqlite3` to avoid adding new dependencies.
"""
from __future__ import annotations

import contextlib
import os
import sqlite3
from pathlib import Path
from typing import Iterator, Optional


DEFAULT_FILENAME = "sampleflow.db"


def _default_db_path() -> Path:
    """Return default DB path at the project root (two parents up).

    File layout: <workspace-root>/sampleflow.db
    """
    return Path(__file__).resolve().parents[2] / DEFAULT_FILENAME


def get_db_path(path: Optional[str] = None) -> Path:
    return Path(path) if path else _default_db_path()


def _migrate_db(conn: sqlite3.Connection) -> None:
    """Add any columns introduced after the initial schema (idempotent)."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(samples)").fetchall()}
    if "sample_type" not in existing:
        conn.execute("ALTER TABLE samples ADD COLUMN sample_type TEXT")


def _apply_pragmas(conn: sqlite3.Connection) -> None:
    cur = conn.cursor()
    # Enable WAL journaling mode when supported; fallback to DELETE otherwise.
    try:
        cur.execute("PRAGMA journal_mode=WAL;")
    except sqlite3.OperationalError:
        try:
            cur.execute("PRAGMA journal_mode=DELETE;")
        except sqlite3.Error:
            pass
    # Recommended pragmas for performance and safety
    cur.execute("PRAGMA synchronous = NORMAL;")
    cur.execute("PRAGMA foreign_keys = ON;")
    cur.close()


def init_db(path: Optional[str] = None) -> None:
    """Initialize database file and ensure `samples` table exists.

    This sets WAL mode and creates the table if missing. Safe to call
    multiple times (idempotent).
    """
    db_path = get_db_path(path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        _create_samples_table(conn)
        _migrate_db(conn)
        conn.commit()
    finally:
        conn.close()


@contextlib.contextmanager
def get_connection(path: Optional[str] = None) -> Iterator[sqlite3.Connection]:
    """Context manager that yields a configured sqlite3.Connection.

    Ensures the same pragmas as `init_db` are applied on each connection.
    Example:
        with get_connection() as conn:
            cur = conn.execute("SELECT ...")
    """
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    try:
        _apply_pragmas(conn)
        yield conn
    finally:
        conn.close()


def _create_samples_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT UNIQUE,
            file_name TEXT,
            file_size INTEGER,
            file_hash TEXT,
            bpm INTEGER,
            audio_key TEXT,
            is_duplicate INTEGER DEFAULT 0,
            sample_type TEXT
        )
        """
    )


def insert_sample(
    file_path: str,
    file_name: str,
    file_size: int,
    file_hash: str,
    bpm: Optional[int] = None,
    audio_key: Optional[str] = None,
    is_duplicate: int = 0,
    sample_type: Optional[str] = None,
    path: Optional[str] = None,
) -> int:
    """Insert or update a sample row. Returns the row id.

    Uses ``ON CONFLICT(file_path) DO UPDATE`` to refresh metadata if the file
    already exists.  ``sample_type`` is only written when non-NULL so that a
    manually-corrected type is never overwritten by a re-scan.
    """
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        conn.execute(
            """
            INSERT INTO samples
                (file_path, file_name, file_size, file_hash, bpm, audio_key,
                 is_duplicate, sample_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(file_path) DO UPDATE SET
                file_name     = excluded.file_name,
                file_size     = excluded.file_size,
                file_hash     = excluded.file_hash,
                bpm           = COALESCE(excluded.bpm,         samples.bpm),
                audio_key     = COALESCE(excluded.audio_key,   samples.audio_key),
                is_duplicate  = excluded.is_duplicate,
                sample_type   = COALESCE(excluded.sample_type, samples.sample_type)
            """,
            (file_path, file_name, file_size, file_hash, bpm, audio_key,
             is_duplicate, sample_type),
        )
        conn.commit()
        row = conn.execute("SELECT id FROM samples WHERE file_path = ?", (file_path,)).fetchone()
        return int(row[0]) if row else -1
    finally:
        conn.close()


def update_sample_by_path(file_path: str, bpm: Optional[int] = None, audio_key: Optional[str] = None, is_duplicate: Optional[int] = None, path: Optional[str] = None) -> None:
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        fields = []
        params = []
        if bpm is not None:
            fields.append("bpm = ?")
            params.append(bpm)
        if audio_key is not None:
            fields.append("audio_key = ?")
            params.append(audio_key)
        if is_duplicate is not None:
            fields.append("is_duplicate = ?")
            params.append(is_duplicate)
        if not fields:
            return
        params.append(file_path)
        conn.execute(f"UPDATE samples SET {', '.join(fields)} WHERE file_path = ?", tuple(params))
        conn.commit()
    finally:
        conn.close()


def update_sample_type(file_path: str, sample_type: Optional[str], path: Optional[str] = None) -> None:
    """Overwrite the sample_type for a single row (used by manual UI edits)."""
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        conn.execute(
            "UPDATE samples SET sample_type = ? WHERE file_path = ?",
            (sample_type, file_path),
        )
        conn.commit()
    finally:
        conn.close()


def delete_samples_smaller_than(file_size: int, path: Optional[str] = None) -> int:
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        cur = conn.execute("DELETE FROM samples WHERE file_size < ?", (file_size,))
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def delete_all_samples(path: Optional[str] = None) -> int:
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        cur = conn.execute("DELETE FROM samples")
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def delete_missing_files(path: Optional[str] = None) -> int:
    """Delete rows whose file_path no longer exists on disk.

    Returns the number of rows removed.
    """
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        rows = conn.execute("SELECT file_path FROM samples").fetchall()
        missing = [row[0] for row in rows if not os.path.exists(row[0])]
        if not missing:
            return 0
        conn.executemany("DELETE FROM samples WHERE file_path = ?", [(p,) for p in missing])
        conn.commit()
        return len(missing)
    finally:
        conn.close()


def fetch_sample(sample_id: int = None, file_path: str = None, path: Optional[str] = None) -> Optional[sqlite3.Row]:
    """Return sample row by id or file_path."""
    if sample_id is None and file_path is None:
        return None
    # Ensure DB and table exist
    init_db(path)
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        if sample_id is not None:
            cur = conn.execute("SELECT * FROM samples WHERE id = ?", (sample_id,))
        else:
            cur = conn.execute("SELECT * FROM samples WHERE file_path = ?", (file_path,))
        return cur.fetchone()
    finally:
        conn.close()


def query_samples(search: Optional[str] = None, duplicates_only: bool = False, path: Optional[str] = None):
    # Ensure DB and table exist
    init_db(path)
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        sql = "SELECT * FROM samples"
        clauses = []
        params = []
        if duplicates_only:
            clauses.append("is_duplicate = 1")
        if search:
            clauses.append("file_name LIKE ?")
            params.append(f"%{search}%")
        if clauses:
            sql += " WHERE " + " AND ".join(clauses)
        sql += " ORDER BY file_name COLLATE NOCASE"
        cur = conn.execute(sql, tuple(params))
        return cur.fetchall()
    finally:
        conn.close()


def rename_sample_path(old_path: str, new_path: str, path: Optional[str] = None) -> None:
    """Update file_path and file_name for a sample row (used after physical file move)."""
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        conn.execute(
            "UPDATE samples SET file_path = ?, file_name = ? WHERE file_path = ?",
            (new_path, Path(new_path).name, old_path),
        )
        conn.commit()
    finally:
        conn.close()


def delete_sample_by_path(file_path: str, path: Optional[str] = None) -> None:
    db_path = get_db_path(path)
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    try:
        conn.row_factory = sqlite3.Row
        _apply_pragmas(conn)
        conn.execute("DELETE FROM samples WHERE file_path = ?", (file_path,))
        conn.commit()
    finally:
        conn.close()
