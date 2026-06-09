import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

load_dotenv()

token = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_TOKEN")
print("HF token:", "yes" if token else "no")

from huggingface_hub import hf_hub_download, list_repo_files

task_id = "99c9cc74-fdc8-46c6-8f8d-3ce2d3bfeea3"
file_name = f"{task_id}.mp3"

try:
    files = list_repo_files("gaia-benchmark/GAIA", repo_type="dataset", token=token)
    print("repo files:", len(files))
    matches = [f for f in files if task_id in f]
    print("matches:", matches[:5])
except Exception as exc:
    print("list_repo_files failed:", exc)
    matches = []

candidates = matches or [
    f"2023/validation/{file_name}",
    f"2023/test/{file_name}",
    f"2023/level1/validation/{file_name}",
    file_name,
]

for path in candidates:
    try:
        local = hf_hub_download(
            "gaia-benchmark/GAIA",
            filename=path,
            repo_type="dataset",
            token=token,
        )
        print("DOWNLOAD OK:", path, "->", local)
        break
    except Exception as exc:
        print("fail:", path, str(exc)[:150])
