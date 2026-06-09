# test_gaia.py
"""Sanity-check script for the GAIA client.

Run this to verify that the scoring API is reachable and returning data.
"""

import json
from gaia_client import get_random_question, get_questions

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Fetching a random GAIA question...")
    print("=" * 60)

    try:
        q = get_random_question()
        print(json.dumps(q, indent=2))
    except Exception as e:
        print(f"❌ get_random_question() failed: {e}")

    print("\n" + "=" * 60)
    print("📋 Fetching full question list (first 3)...")
    print("=" * 60)

    try:
        questions = get_questions()
        for i, item in enumerate(questions[:3]):
            task_id = item.get("task_id", "N/A")
            question = str(item.get("question", ""))[:120]
            file_name = item.get("file_name", "None")
            print(f"\n[{i}] task_id  : {task_id}")
            print(f"     file     : {file_name}")
            print(f"     question : {question}...")
        print(f"\n✅ Total questions available: {len(questions)}")
    except Exception as e:
        print(f"❌ get_questions() failed: {e}")
