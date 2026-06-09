# Hugging Face Agents Course Portfolio 🤖

Welcome to my repository for the Hugging Face Agents course! This portfolio houses the projects and agents I built throughout this unit, showcasing advanced implementations of autonomous LLM agents, routing mechanisms, database caching, and tracing.

---

## 📜 Course Certificate
My completion certificate is available here:  
👉 **[View Course Certificate (PDF)](Gala_agent/certificate.pdf)**

---

## 📁 Repository Structure & Analysis

The repository contains three primary agent implementations, along with testing scripts and helper modules:

```
HF_agent/
│
├── Gala_agent/                 # Main GAIA Assistant agent project folder
│   ├── app.py                  # Gradio API endpoint and local agent runner
│   ├── tools.py                # Core agent toolset (PDF, Excel, Web Search, Python Executor, etc.)
│   ├── gaia_runner.py          # Benchmark scorer script for scoring answers on GAIA Dataset
│   └── certificate.pdf         # Course completion certificate
│
├── Gatekeeper_agent/           # LangGraph-based spam filtering email assistant (Jarvis)
│   └── app.py                  # Categorizer, auto-reply draft, and notification graph
│
├── Vision_react_agent/         # Multimodal ReAct butler agent (Jarvis)
│   ├── app.py                  # Vision-capable tool graph parsing image inputs (Capture.PNG)
│   └── Capture.PNG             # Sample image containing hand-written notes for extraction
│
└── push_all.bat                # Automation script to resolve Git issues and push to origin
```

---

## 🚀 Agent Breakdown & Key Capabilities

### 1. Gala Agent (GAIA Benchmark Assistant)
* **Goal**: An autonomous agent designed to solve complex multi-modal reasoning tasks from the GAIA Benchmark dataset.
* **Key Components**:
  * `app.py`: Powers the backend using **FastAPI** and integrates with a **Gradio** workspace for submission.
  * `tools.py`: Equips the agent with a rich tool suite:
    * `python_executor_tool`: Runs generated code locally to solve math and data tasks.
    * `pdf_reader_tool` & `excel_reader_tool`: Parses complex multi-page documents.
    * `youtube_transcript_tool`: Downloads and summarizes audio transcripts.
    * `web_search_tool` & `tavily_search_tool`: Fetches live data from the web.
  * **Memory & Tracing**: 
    * Synchronizes task statuses and file uploads with **Supabase Storage** and Postgres database (`supabase_gaia.py`).
    * Leverages **Langfuse** (`CallbackHandler`) to trace every single LLM call and tool execution for full debugging observability.

### 2. Gatekeeper Agent (Jarvis the Email Butler)
* **Goal**: Automates incoming email classification, filters spam, and prepares drafts for the user.
* **Key Components**:
  * Utilizes **LangGraph** to build a conditional state transition graph:
    1. **`read_email`**: Processes sender, subject, and body details.
    2. **`classify_email`**: Uses a free Llama 3.3 model from OpenRouter to determine if the message is `SPAM` or `HAM`.
    3. **`handle_spam` / `draft_response`**: Moves spam to folders or drafts a context-aware response for legitimate mail.
    4. **`notify_mr_gaurav`**: Displays the prepared draft to the terminal for manual review.

### 3. Vision ReAct Agent (Jarvis Multimodal)
* **Goal**: Parses physical or handwritten documents using vision LLMs and calculates results using custom tools.
* **Key Components**:
  * Integrates **Llama-3.3-70b-instruct** via OpenRouter.
  * Extracts text from local images (`Capture.PNG`) using Base64 encoding.
  * Uses a structured ReAct loop in **LangGraph** to decide when to call the vision extractor tool or run math operations (`divide`) to address the user's query about personal schedules and regimes.

---

## 🛠️ Technology Stack Used
* **Orchestration**: `LangChain`, `LangGraph` (StateGraph)
* **Models**: `Meta Llama 3.3 70B Instruct` (via OpenRouter), `Gemini 2.5 Flash`
* **Observability & Tracing**: `Langfuse`
* **Backend Database & Storage**: `Supabase` (Postgres + Storage Buckets)
* **Interfaces**: `Gradio`, `FastAPI`

---
*Developed by Gaurav Punetha*
