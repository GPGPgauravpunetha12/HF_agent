# HF Space deployment (lightweight)

The course **Final_Assignment_Template** Space cannot run the full GAIA agent.

## Why the Space is not enough

| Requirement | Free HF Space | Your local `Gala_agent` |
|-------------|---------------|-------------------------|
| Ollama / local LLM | No | Yes |
| Whisper audio | Too heavy | Yes |
| Torch / transformers | Too large | Yes |
| 20 GAIA tasks × tools | Timeout | Yes |
| GAIA file downloads | Broken API + gated dataset | Hub fallback |

## What the Space is for

The scoring API only needs:
- Your **username**
- A public **`agent_code`** URL (this Space repo)
- **Pre-computed answers** (from local `gaia_runner.py`)

It does **not** run your agent on the Space.

## Deploy

Copy `hf_space/app.py` and `hf_space/requirements.txt` to your Space repo root, then push.

## Run the real agent (local)

```powershell
cd Gala_agent
$env:LLM_PROVIDER="ollama"
python gaia_runner.py
```

Choose `all`, then `submit` or upload `gaia_progress.json` to the Space.
