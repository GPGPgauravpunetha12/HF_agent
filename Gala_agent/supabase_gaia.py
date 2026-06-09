"""Push GAIA task files and run metadata to Supabase Storage + Postgres."""

from __future__ import annotations

import mimetypes
import os
from pathlib import Path
from typing import Any

from supabase_client import GAIA_FILES_BUCKET, get_supabase, is_supabase_configured

_supabase_warned = False


def _warn_supabase_once(exc: Exception) -> None:
    global _supabase_warned
    if _supabase_warned:
        return
    _supabase_warned = True
    print(
        f"⚠️  Supabase sync skipped: {exc}\n"
        "   Run supabase/migrations/001_gaia_tasks.sql in your Supabase SQL Editor, "
        "or remove SUPABASE_URL from .env to disable sync."
    )


def _storage_path(task_id: str, filename: str) -> str:
    safe_name = Path(filename).name
    return f"{task_id}/{safe_name}"


def upload_gaia_file(
    task_id: str,
    local_path: str,
    *,
    file_name: str | None = None,
) -> dict[str, Any] | None:
    """Upload a local GAIA file to Supabase Storage. Returns metadata or None."""
    if not is_supabase_configured():
        return None

    path = Path(local_path)
    if not path.is_file():
        return None

    filename = file_name or path.name
    remote_path = _storage_path(task_id, filename)
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    try:
        client = get_supabase()
        with open(path, "rb") as f:
            client.storage.from_(GAIA_FILES_BUCKET).upload(
                remote_path,
                f,
                file_options={"content-type": content_type, "upsert": "true"},
            )

        public_url = client.storage.from_(GAIA_FILES_BUCKET).get_public_url(remote_path)

        return {
            "task_id": task_id,
            "file_name": filename,
            "local_path": str(path),
            "storage_path": remote_path,
            "public_url": public_url,
            "content_type": content_type,
            "size_bytes": path.stat().st_size,
        }
    except Exception as exc:
        _warn_supabase_once(exc)
        return None


def upsert_gaia_task(
    task_id: str,
    *,
    question: str = "",
    file_name: str | None = None,
    storage_path: str | None = None,
    public_url: str | None = None,
    analysis_preview: str | None = None,
    answer: str | None = None,
    status: str = "pending",
) -> dict[str, Any] | None:
    """Upsert GAIA task metadata into the gaia_tasks table."""
    if not is_supabase_configured():
        return None

    row: dict[str, Any] = {
        "task_id": task_id,
        "question": question,
        "file_name": file_name,
        "storage_path": storage_path,
        "public_url": public_url,
        "analysis_preview": analysis_preview,
        "answer": answer,
        "status": status,
    }

    try:
        client = get_supabase()
        result = (
            client.table("gaia_tasks")
            .upsert(row, on_conflict="task_id")
            .execute()
        )
        return result.data[0] if result.data else row
    except Exception as exc:
        _warn_supabase_once(exc)
        return None


def sync_gaia_task_from_local(
    task: dict[str, Any],
    local_path: str | None,
    *,
    analysis_preview: str | None = None,
    answer: str | None = None,
    status: str = "processing",
) -> dict[str, Any] | None:
    """Upload file (if present) and upsert task row for a GAIA task."""
    if not is_supabase_configured():
        return None

    task_id = task.get("task_id", "")
    question = task.get("question", "")
    file_name = task.get("file_name") or (Path(local_path).name if local_path else None)

    upload_meta = None
    if local_path and os.path.isfile(local_path):
        upload_meta = upload_gaia_file(task_id, local_path, file_name=file_name)

    return upsert_gaia_task(
        task_id,
        question=question,
        file_name=file_name,
        storage_path=upload_meta["storage_path"] if upload_meta else None,
        public_url=upload_meta["public_url"] if upload_meta else None,
        analysis_preview=analysis_preview,
        answer=answer,
        status=status,
    )


def get_gaia_task(task_id: str) -> dict[str, Any] | None:
    """Fetch a GAIA task record from Supabase."""
    if not is_supabase_configured():
        return None

    try:
        client = get_supabase()
        result = (
            client.table("gaia_tasks")
            .select("*")
            .eq("task_id", task_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None
    except Exception as exc:
        _warn_supabase_once(exc)
        return None
