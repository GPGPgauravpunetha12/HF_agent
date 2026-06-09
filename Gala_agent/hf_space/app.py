"""
Hugging Face Space — lightweight GAIA submission UI.

This Space is NOT meant to run the full local agent (Ollama, Whisper, PDF, etc.).
Free HF Spaces lack CPU/RAM/time for that.

Course workflow:
  1. Run the full agent locally:  python gaia_runner.py
  2. This Space hosts your public agent code URL for scoring verification.
  3. Submit answers from local gaia_runner (or use this UI to re-submit cached answers).

Set Space secrets: OPENROUTER_API_KEY (optional, for demo questions only)
"""

import json
import os
import gradio as gr
import requests

DEFAULT_API_URL = "https://agents-course-unit4-scoring.hf.space"


def _space_urls():
    space_id = os.getenv("SPACE_ID", "")
    space_host = os.getenv("SPACE_HOST", "")
    if space_host and not space_host.startswith("http"):
        runtime_url = (
            space_host
            if space_host.endswith(".hf.space")
            else f"https://{space_host}.hf.space"
        )
    else:
        runtime_url = space_host or "(local)"
    agent_code = f"https://huggingface.co/spaces/{space_id}/tree/main" if space_id else ""
    return runtime_url, agent_code


def _run_local_style_agent(question: str) -> str:
    """Optional: call OpenRouter if key is set. Otherwise return a clear placeholder."""
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return (
            "Run the full agent locally with: python gaia_runner.py\n"
            "This Space only provides the public code link for course submission."
        )
    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage

        llm = ChatOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            model="google/gemini-2.5-flash",
            temperature=0,
            max_tokens=1024,
        )
        return llm.invoke([HumanMessage(content=question)]).content.strip()
    except Exception as exc:
        return f"Space demo LLM error: {exc}"


def submit_cached_answers(profile: gr.OAuthProfile | None):
    """Submit answers already saved by local gaia_runner.py (gaia_progress.json)."""
    if not profile:
        return "Log in to Hugging Face first.", None

    _, agent_code = _space_urls()
    progress_path = os.getenv("GAIA_PROGRESS_FILE", "gaia_progress.json")

    if not os.path.isfile(progress_path):
        return (
            f"No {progress_path} found in this Space.\n\n"
            "Run locally:\n"
            "  python gaia_runner.py\n"
            "Then upload gaia_progress.json to the Space Files tab, or submit from your PC.",
            None,
        )

    with open(progress_path, encoding="utf-8") as f:
        progress = json.load(f)

    if not progress:
        return "gaia_progress.json is empty.", None

    answers = [
        {"task_id": tid, "submitted_answer": ans}
        for tid, ans in progress.items()
    ]
    payload = {
        "username": profile.username,
        "agent_code": agent_code,
        "answers": answers,
    }

    try:
        resp = requests.post(f"{DEFAULT_API_URL}/submit", json=payload, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        status = (
            f"Submitted {len(answers)} cached answer(s).\n"
            f"Score: {data.get('score')}% — {data.get('message')}"
        )
        rows = [{"task_id": a["task_id"], "answer": a["submitted_answer"][:120]} for a in answers]
        return status, rows
    except Exception as exc:
        return f"Submit failed: {exc}", None


def run_demo_single(question: str):
    return _run_local_style_agent(question)


with gr.Blocks(title="GAIA Agent — Space UI") as demo:
    runtime_url, agent_code = _space_urls()
    gr.Markdown(
        f"""
# GAIA Agent — Hugging Face Space (submission UI)

**This Space is not enough to run the full agent.** Use your PC for real runs.

| Where | What runs |
|-------|-----------|
| **Your PC** (`Gala_agent/`) | Ollama, Whisper, PDF/Excel/image tools, file downloads, `gaia_runner.py` |
| **This Space** | Public code link + optional cached-answer submit |

- Runtime: `{runtime_url}`
- Agent code URL: `{agent_code or "set SPACE_ID"}`

### Recommended workflow
1. On your PC: `python gaia_runner.py` → choose `all` → answers saved to `gaia_progress.json`
2. Upload `gaia_progress.json` to this Space (Files tab), or submit from PC
3. Click **Submit cached answers** below (after HF login)
"""
    )

    gr.LoginButton()
    gr.Markdown("### Submit answers computed locally")
    submit_btn = gr.Button("Submit cached gaia_progress.json")
    submit_status = gr.Textbox(label="Submit status", lines=6)
    submit_table = gr.JSON(label="Submitted tasks")

    submit_btn.click(submit_cached_answers, outputs=[submit_status, submit_table])

    gr.Markdown("### Demo single question (OpenRouter only, optional)")
    q_in = gr.Textbox(label="Question", lines=3)
    a_out = gr.Textbox(label="Answer", lines=5)
    gr.Button("Run demo").click(run_demo_single, inputs=q_in, outputs=a_out)


if __name__ == "__main__":
    print("-" * 30 + " App Starting " + "-" * 30)
    runtime_url, agent_code = _space_urls()
    print(f"Runtime URL: {runtime_url}")
    print(f"Agent code:  {agent_code}")
    print("-" * 72)
    demo.launch()
