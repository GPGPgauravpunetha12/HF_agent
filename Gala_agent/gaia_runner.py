# gaia_runner.py
"""GAIA benchmark runner.

Fetches questions from the scoring API, runs the LangGraph agent on each,
and submits the answers back for scoring.
"""

import os
import json
import uuid
import requests
import time

from app import run_agent
from gaia_client import get_questions, download_task_file
from file_router import analyze_file
from supabase_client import is_supabase_configured
from supabase_gaia import sync_gaia_task_from_local

SUBMIT_URL = "https://agents-course-unit4-scoring.hf.space/submit"
PROGRESS_FILE = "gaia_progress.json"
HF_USERNAME = "jklkdkfl"
AGENT_CODE_URL = "https://huggingface.co/spaces/jklkdkfl/Final_Assignment_Template/tree/main"


# ─────────────────────────────────────────────
# Progress cache helpers
# ─────────────────────────────────────────────

def load_progress() -> dict:
    """Load cached answers so we don't re-process completed tasks."""
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r") as f:
            return json.load(f)
    return {}


def save_progress(progress: dict) -> None:
    """Persist answered task_ids to disk."""
    with open(PROGRESS_FILE, "w") as f:
        json.dump(progress, f, indent=2)
    print(f"💾 Progress saved ({len(progress)} tasks).")


# ─────────────────────────────────────────────
# Per-task runner
# ─────────────────────────────────────────────

def run_task(task: dict) -> str:
    """Run the agent on a single GAIA task and return the answer string."""
    task_id  = task.get("task_id", "")
    question = task.get("question", "")
    file_name = task.get("file_name", "")

    print(f"\n{'='*70}")
    print(f"📌 Task ID : {task_id}")
    print(f"📂 File    : {file_name or 'None'}")
    print(f"❓ Question: {question[:200]}")
    print("=" * 70)

    # ── Download + analyze file, push to Supabase when configured ────────
    local_path = None
    analysis_preview = None

    if file_name:
        print(f"\n📥 Downloading file for task {task_id}...")
        local_path = download_task_file(task_id, file_name=file_name)
        if local_path:
            print(f"✅ Saved locally: {local_path}")
            print("🔍 Analyzing file...")
            analysis_preview = analyze_file(local_path)
            if is_supabase_configured():
                print("☁️  Syncing file + task to Supabase...")
                sync_gaia_task_from_local(
                    task,
                    local_path,
                    analysis_preview=analysis_preview[:4000] if analysis_preview else None,
                    status="processing",
                )
        else:
            print("⚠️  File download failed.")

    # ── Build prompt ───────────────────────────────────────────────────────
    if file_name:
        prompt = (
            f"Task ID: {task_id}\n"
            f"Attached File: {file_name}\n\n"
            f"Question: {question}"
        )
        if analysis_preview:
            prompt += (
                f"\n\n--- File analysis preview ---\n"
                f"{analysis_preview[:6000]}"
            )
    else:
        prompt = f"Task ID: {task_id}\nQuestion: {question}"
        if is_supabase_configured():
            sync_gaia_task_from_local(task, None, status="processing")

    # ── Invoke agent ───────────────────────────────────────────────────────
    print("\n🚀 Running agent... please wait.\n")
    thread_id = str(uuid.uuid4())
    answer = run_agent(prompt, thread_id)

    if is_supabase_configured():
        saved = sync_gaia_task_from_local(
            task,
            local_path,
            analysis_preview=analysis_preview[:4000] if analysis_preview else None,
            answer=answer,
            status="completed",
        )
        if saved:
            print("☁️  Task result saved to Supabase.")

    print(f"\n🎩 Agent answer: {answer}")
    return answer


# ─────────────────────────────────────────────
# Submission
# ─────────────────────────────────────────────

def submit_answers(answers: list) -> None:
    """POST the collected answers to the scoring endpoint."""
    payload = {
        "username": HF_USERNAME,
        "agent_code": AGENT_CODE_URL,
        "answers": answers,
    }
    print(f"\n📤 Submitting {len(answers)} answer(s)...")
    try:
        resp = requests.post(SUBMIT_URL, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        print("✅ Submission accepted!")
        print(json.dumps(result, indent=2))
    except requests.HTTPError as http_err:
        print(f"❌ HTTP error during submission: {http_err}")
        print(resp.text)
    except Exception as err:
        print(f"❌ Submission failed: {err}")


# ─────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────

def main():
    print("\n🎩 GAIA Runner — Alfred Agent\n")

    # Fetch all questions from API
    print("📋 Fetching questions from GAIA API...")
    try:
        questions = get_questions()
    except Exception as e:
        print(f"❌ Failed to fetch questions: {e}")
        return

    print(f"✅ {len(questions)} questions received.\n")

    # Load existing progress (cached answers)
    progress = load_progress()
    print(f"📂 Cached answers: {len(progress)}\n")

    # Show question list and let user choose
    print(f"{'─'*70}")
    print(f"{'#':<4} {'Task ID':<40} {'File':<15} Question")
    print(f"{'─'*70}")
    for i, task in enumerate(questions):
        tid = task.get("task_id", "")[:36]
        fn  = (task.get("file_name") or "")[:14]
        q   = task.get("question", "")[:50]
        cached = "✓" if tid in progress else " "
        print(f"[{cached}] {i:<3} {tid:<38} {fn:<15} {q}...")

    print(f"{'─'*70}")
    print("\nOptions:")
    print("  Enter a number  → run that single question")
    print("  'all'           → run ALL questions (skips cached)")
    print("  'force'         → run ALL questions (clears cache)")
    print("  'submit'        → submit cached answers only")
    print("  'q'             → quit\n")

    choice = input("Your choice: ").strip().lower()

    # ── Quit ──────────────────────────────────────────────────────────────
    if choice in ("q", "quit", "exit"):
        print("👋 Bye!")
        return

    # ── Submit cached only ────────────────────────────────────────────────
    if choice == "submit":
        if not progress:
            print("⚠️  No cached answers to submit.")
            return
        answers = [{"task_id": tid, "submitted_answer": ans}
                   for tid, ans in progress.items()]
        submit_answers(answers)
        return

    # ── Determine which tasks to run ──────────────────────────────────────
    if choice == "force":
        progress = {}
        save_progress(progress)
        tasks_to_run = questions
        print(f"\n▶️  Running {len(tasks_to_run)} task(s) (cache cleared)…\n")
    elif choice == "all":
        tasks_to_run = [t for t in questions
                        if t.get("task_id", "") not in progress]
        print(f"\n▶️  Running {len(tasks_to_run)} uncached task(s)…\n")
    else:
        try:
            idx = int(choice)
            tasks_to_run = [questions[idx]]
        except (ValueError, IndexError):
            print("❌ Invalid choice.")
            return

    # ── Process tasks ─────────────────────────────────────────────────────
    new_answers = []
    for task in tasks_to_run:
        tid = task.get("task_id", "")
        try:
            answer = run_task(task)
            progress[tid] = answer
            new_answers.append({"task_id": tid, "submitted_answer": answer})
            save_progress(progress)
            time.sleep(5)
        except Exception as e:
            print(f"❌ Task {tid} failed: {e}")
            import traceback
            traceback.print_exc()

    # ── Ask whether to submit ─────────────────────────────────────────────
    if new_answers:
        print(f"\n✅ Processed {len(new_answers)} task(s).")
        do_submit = input("\nSubmit answers now? (y/n): ").strip().lower()
        if do_submit == "y":
            all_answers = [{"task_id": tid, "submitted_answer": ans}
                           for tid, ans in progress.items()]
            submit_answers(all_answers)
        else:
            print("💾 Answers saved. Run again and choose 'submit' when ready.")


if __name__ == "__main__":
    main()
