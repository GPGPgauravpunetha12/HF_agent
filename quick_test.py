# quick_test.py
"""Non-interactive end-to-end test: picks question index 0 from the API and runs the agent."""

import uuid
from gaia_client import get_questions, download_task_file
from file_router import analyze_file
from app import run_agent

def run_task(task):
    task_id  = task.get("task_id", "")
    question = task.get("question", "")
    file_name = task.get("file_name", "")

    print(f"\n{'='*70}")
    print(f"📌 Task ID : {task_id}")
    print(f"📂 File    : {file_name or 'None'}")
    print(f"❓ Question: {question}")
    print("=" * 70)

    file_content = ""
    if file_name:
        print("⬇️  Downloading attached file...")
        file_path = download_task_file(task_id, file_name=file_name)
        if file_path:
            print(f"✅ Downloaded → {file_path}")
            file_content = analyze_file(file_path)
            print(f"📄 File preview: {file_content[:300]}")
        else:
            print("⚠️  File download failed.")

    if file_content:
        prompt = (
            f"Task ID: {task_id}\n"
            f"Attached File: {file_name}\n"
            f"File Content:\n{file_content}\n\n"
            f"Question: {question}"
        )
    else:
        prompt = f"Task ID: {task_id}\nQuestion: {question}"

    print("\n🚀 Running agent...\n")
    answer = run_agent(prompt, str(uuid.uuid4()))
    print(f"\n🎩 Agent Answer: {answer}")
    return answer

if __name__ == "__main__":
    print("📋 Fetching GAIA questions...")
    questions = get_questions()
    print(f"✅ {len(questions)} questions. Running question 0...\n")
    task = questions[0]
    run_task(task)
