import os
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://agents-course-unit4-scoring.hf.space"
GAIA_DATASET_ID = "gaia-benchmark/GAIA"
DOWNLOADS_DIR = "downloads"

_task_file_path_cache: Dict[str, str] = {}


def _hf_token() -> Optional[str]:
    return (
        os.getenv("HUGGINGFACEHUB_API_TOKEN")
        or os.getenv("HF_TOKEN")
        or os.getenv("HUGGING_FACE_HUB_TOKEN")
    )


def get_questions() -> List[Dict[str, Any]]:
    """Fetch the full list of GAIA questions."""
    response = requests.get(f"{BASE_URL}/questions", timeout=60)
    response.raise_for_status()
    return response.json()


def get_random_question() -> Dict[str, Any]:
    """Fetch a single random question (used for quick sanity checks)."""
    response = requests.get(f"{BASE_URL}/random-question", timeout=60)
    response.raise_for_status()
    return response.json()


@lru_cache(maxsize=1)
def _build_task_file_path_index() -> Dict[str, str]:
    """Map task_id -> GAIA dataset repo path (e.g. 2023/validation/foo.mp3)."""
    token = _hf_token()
    if not token:
        return {}

    try:
        from huggingface_hub import list_repo_files

        files = list_repo_files(GAIA_DATASET_ID, repo_type="dataset", token=token)
    except Exception as exc:
        print(f"⚠️  Could not list GAIA dataset files: {exc}")
        return {}

    index: Dict[str, str] = {}
    pattern = re.compile(
        r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})",
        re.IGNORECASE,
    )
    for path in files:
        match = pattern.search(path)
        if match:
            index[match.group(1).lower()] = path
    return index


def _download_from_hf_hub(task_id: str, file_name: Optional[str] = None) -> Optional[str]:
    """Fallback: download attachment from gaia-benchmark/GAIA on Hugging Face Hub."""
    token = _hf_token()
    if not token:
        print(
            "⚠️  HF scoring API has no file for this task. "
            "Set HUGGINGFACEHUB_API_TOKEN in .env and accept access at "
            "https://huggingface.co/datasets/gaia-benchmark/GAIA"
        )
        return None

    global _task_file_path_cache
    if not _task_file_path_cache:
        _task_file_path_cache = _build_task_file_path_index()

    repo_path = _task_file_path_cache.get(task_id.lower())
    if not repo_path and file_name:
        repo_path = f"2023/validation/{file_name}"

    if not repo_path:
        print(f"⚠️  No GAIA hub path found for task {task_id}")
        return None

    try:
        from huggingface_hub import hf_hub_download

        local_path = hf_hub_download(
            GAIA_DATASET_ID,
            filename=repo_path,
            repo_type="dataset",
            token=token,
        )
    except Exception as exc:
        err = str(exc)
        if "403" in err or "gated" in err.lower():
            print(
                f"⚠️  GAIA dataset access denied for task {task_id}. "
                "Visit https://huggingface.co/datasets/gaia-benchmark/GAIA "
                "and click 'Agree and access repository', then retry."
            )
        else:
            print(f"⚠️  HF hub download failed for task {task_id}: {exc}")
        return None

    os.makedirs(DOWNLOADS_DIR, exist_ok=True)
    out_name = file_name or os.path.basename(repo_path)
    dest = os.path.join(DOWNLOADS_DIR, out_name)
    if os.path.abspath(local_path) != os.path.abspath(dest):
        with open(local_path, "rb") as src, open(dest, "wb") as dst:
            dst.write(src.read())
    return dest


def download_task_file(
    task_id: str,
    file_name: Optional[str] = None,
) -> Optional[str]:
    """Download the file for a GAIA task.

    Strategy:
    1. HF scoring API  GET /files/{task_id}
    2. Fallback: gaia-benchmark/GAIA on Hugging Face Hub

    The scoring API is often broken (known HF Space bug — returns 404 even when
    file_name is present). Hub fallback requires GAIA dataset access on your HF account.
    """
    url = f"{BASE_URL}/files/{task_id}"
    response = requests.get(url, timeout=120)

    if response.status_code == 200:
        content_disp = response.headers.get("content-disposition")
        if content_disp and "filename=" in content_disp:
            filename = content_disp.split("filename=")[1].strip('"')
        else:
            filename = file_name or task_id

        os.makedirs(DOWNLOADS_DIR, exist_ok=True)
        path = os.path.join(DOWNLOADS_DIR, filename)
        with open(path, "wb") as f:
            f.write(response.content)
        return path

    if response.status_code == 404:
        detail = ""
        try:
            detail = response.json().get("detail", "")
        except Exception:
            detail = response.text[:200]
        print(
            f"⚠️  Scoring API has no file for task {task_id} (HTTP 404). "
            f"{detail} — trying Hugging Face GAIA dataset..."
        )
    else:
        print(
            f"⚠️  Scoring API download failed for task {task_id}: "
            f"HTTP {response.status_code}"
        )

    return _download_from_hf_hub(task_id, file_name=file_name)
