"""
Local OpenAI-compatible inference server for google/gemma-4-12B-it.

Exposes POST /v1/chat/completions so LangChain's ChatOpenAI can connect.

Usage:
    python gemma_server.py                     # auto-detect GPU/CPU
    python gemma_server.py --port 8001         # custom port
    python gemma_server.py --quantize 4bit     # 4-bit quantization (~8 GB VRAM)
    python gemma_server.py --quantize 8bit     # 8-bit quantization (~12 GB VRAM)
    python gemma_server.py --device cpu        # force CPU (very slow)

Requires:
    pip install transformers torch accelerate bitsandbytes fastapi uvicorn
"""

import argparse
import json
import time
import uuid
import os
from typing import List, Optional

import torch
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# CLI args
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Gemma 4 12B local server")
parser.add_argument("--model", default="google/gemma-4-12B-it", help="HF model ID")
parser.add_argument("--port", type=int, default=8001, help="Server port")
parser.add_argument("--host", default="0.0.0.0", help="Bind host")
parser.add_argument(
    "--quantize",
    choices=["none", "4bit", "8bit"],
    default="4bit",
    help="Quantization level (default: 4bit for ~8 GB VRAM)",
)
parser.add_argument(
    "--device",
    choices=["auto", "cpu", "cuda"],
    default="auto",
    help="Device to run on",
)
parser.add_argument(
    "--max-new-tokens",
    type=int,
    default=2048,
    help="Default max new tokens if not specified in request",
)

args, _ = parser.parse_known_args()

# ---------------------------------------------------------------------------
# Load model
# ---------------------------------------------------------------------------
print(f"🔄 Loading model: {args.model}")
print(f"   Quantization : {args.quantize}")
print(f"   Device       : {args.device}")

from transformers import AutoProcessor, AutoModelForMultimodalLM

HF_TOKEN = os.getenv("HUGGINGFACEHUB_API_TOKEN") or os.getenv("HF_TOKEN")

# Build model kwargs
model_kwargs = {"token": HF_TOKEN}

if args.quantize == "4bit":
    from transformers import BitsAndBytesConfig

    model_kwargs["quantization_config"] = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
        bnb_4bit_quant_type="nf4",
    )
    model_kwargs["device_map"] = "auto"
elif args.quantize == "8bit":
    from transformers import BitsAndBytesConfig

    model_kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
    model_kwargs["device_map"] = "auto"
else:
    # Full precision / bfloat16
    model_kwargs["torch_dtype"] = torch.bfloat16
    if args.device == "cpu":
        model_kwargs["device_map"] = "cpu"
    else:
        model_kwargs["device_map"] = "auto"

processor = AutoProcessor.from_pretrained(args.model, token=HF_TOKEN)
model = AutoModelForMultimodalLM.from_pretrained(args.model, **model_kwargs)

print(f"✅ Model loaded successfully on device(s): {model.hf_device_map if hasattr(model, 'hf_device_map') else 'single device'}")

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Gemma 4 12B Local Server", version="1.0.0")


# --- Request/Response schemas (OpenAI-compatible subset) ---

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "gemma-4-12b-it"
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    top_p: Optional[float] = 0.95
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: UsageInfo


# --- Endpoints ---

@app.get("/v1/models")
async def list_models():
    """List available models (OpenAI-compatible)."""
    return {
        "object": "list",
        "data": [
            {
                "id": args.model,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "local",
            }
        ],
    }


@app.get("/health")
async def health():
    return {"status": "ok", "model": args.model}


@app.post("/v1/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Generate a chat completion (OpenAI-compatible)."""
    try:
        # Convert messages to the format Gemma expects
        messages = [{"role": m.role, "content": m.content} for m in request.messages]

        # Tokenize using the processor's chat template
        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            return_dict=True,
            return_tensors="pt",
            add_generation_prompt=True,
            enable_thinking=False,  # Disable thinking for faster responses
        ).to(model.device)

        input_len = inputs["input_ids"].shape[-1]

        # Generation parameters
        max_new = request.max_tokens or args.max_new_tokens
        gen_kwargs = {
            "max_new_tokens": max_new,
            "temperature": max(request.temperature or 1.0, 0.01),  # avoid 0
            "top_p": request.top_p or 0.95,
            "do_sample": (request.temperature or 1.0) > 0.01,
        }

        # Generate
        with torch.no_grad():
            output_ids = model.generate(**inputs, **gen_kwargs)

        # Decode only the new tokens
        new_tokens = output_ids[0][input_len:]
        response_text = processor.decode(new_tokens, skip_special_tokens=True)

        # Strip any remaining thinking tags if present
        if "<|channel>" in response_text:
            # Remove thinking blocks
            import re
            response_text = re.sub(
                r"<\|channel>thought\n.*?<channel\|>",
                "",
                response_text,
                flags=re.DOTALL,
            ).strip()

        output_len = len(new_tokens)

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
            created=int(time.time()),
            model=args.model,
            choices=[
                ChatChoice(
                    message=ChatMessage(role="assistant", content=response_text),
                    finish_reason="stop",
                )
            ],
            usage=UsageInfo(
                prompt_tokens=input_len,
                completion_tokens=output_len,
                total_tokens=input_len + output_len,
            ),
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print(f"\n🚀 Starting Gemma 4 12B server on http://{args.host}:{args.port}")
    print(f"   OpenAI-compatible endpoint: http://localhost:{args.port}/v1/chat/completions")
    print(f"   Health check:               http://localhost:{args.port}/health\n")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
