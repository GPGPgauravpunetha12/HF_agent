import os
import uuid
from typing import Annotated

from dotenv import load_dotenv
from typing_extensions import TypedDict

# =====================================================
# LOAD ENV
# =====================================================

load_dotenv()

# =====================================================
# FASTAPI
# =====================================================

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="GAIA Agent")

class QuestionRequest(BaseModel):
    question: str

# =====================================================
# LANGCHAIN
# =====================================================

from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    SystemMessage,
)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

# =====================================================
# LANGGRAPH
# =====================================================

from langgraph.graph import (
    StateGraph,
    START,
)

from langgraph.graph.message import add_messages

from langgraph.prebuilt import (
    ToolNode,
    tools_condition,
)

from langgraph.checkpoint.memory import MemorySaver

# =====================================================
# LANGFUSE
# =====================================================

from langfuse import Langfuse
from langfuse.langchain import CallbackHandler

# =====================================================
# TOOLS
# =====================================================

from tools import (
    guest_info_tool,
    web_search_tool,
    weather_info_tool,
    hub_stats_tool,
    latest_news_tool,
    youtube_transcript_tool,
    image_info_tool,
    audio_transcriber_tool,
    python_executor_tool,
    excel_reader_tool,
    pdf_reader_tool,
    download_file_tool,
    webpage_reader_tool,
    analyze_file_tool,
    tavily_search_tool,
)

# =====================================================
# LANGFUSE INIT
# =====================================================

langfuse_handler = None

if (
    os.getenv("LANGFUSE_PUBLIC_KEY")
    and os.getenv("LANGFUSE_SECRET_KEY")
):
    Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv(
            "LANGFUSE_BASE_URL",
            "https://cloud.langfuse.com",
        ),
    )

    langfuse_handler = CallbackHandler()

# =====================================================
# STATE
# =====================================================

class AgentState(TypedDict):
    messages: Annotated[
        list[AnyMessage],
        add_messages,
    ]

# =====================================================
# SYSTEM PROMPT
# =====================================================

SYSTEM_PROMPT = """
You are a helpful assistant tasked with answering questions using a set of tools.

Your final answer must strictly follow this format:

FINAL ANSWER: [ANSWER]

Only write the answer in that exact format.

Do not explain anything.
Do not include reasoning.
Do not include markdown.
Do not include code blocks.
Do not include tool traces.
Do not include any text before or after the final answer.

If you are provided with a similar question and its final answer, and the current question is exactly the same, then simply return the same final answer without using any tools.

Only use tools if the current question is different from the similar one.

Examples:

FINAL ANSWER: FunkMonk

FINAL ANSWER: Paris

FINAL ANSWER: 128

When tools are required:
- Use the available tools to find the answer.
- After receiving tool results, return only:
  FINAL ANSWER: [ANSWER]

Never output anything except:
FINAL ANSWER: [ANSWER]
"""

# =====================================================
# MODEL
# =====================================================

def create_llm():

    provider = os.getenv("LLM_PROVIDER", "").lower()

    # =================================================
    # GEMINI
    # =================================================

    if provider == "gemini":
        google_key = os.getenv("GOOGLE_API_KEY")

        if not google_key:
            raise ValueError("GOOGLE_API_KEY missing")

        print("🚀 Using Gemini")

        return ChatGoogleGenerativeAI(
            model=os.getenv(
                "GEMINI_MODEL",
                "gemini-2.5-flash"
            ),
            google_api_key=google_key,
            temperature=0,
            max_output_tokens=8192,
        )

    # =================================================
    # GROQ
    # =================================================

    if provider == "groq":

        groq_key = os.getenv("GROQ_API_KEY")

        if not groq_key:
            raise ValueError("GROQ_API_KEY missing")

        model = os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile"
        )

        print(f"⚡ Using Groq: {model}")

        return ChatGroq(
            groq_api_key=groq_key,
            model_name=model,
            temperature=0,
        )

    # =================================================
    # OPENROUTER
    # =================================================

    if provider == "openrouter":

        openrouter_key = os.getenv(
            "OPENROUTER_API_KEY"
        )

        if not openrouter_key:
            raise ValueError(
                "OPENROUTER_API_KEY missing"
            )

        model = os.getenv(
            "OPENROUTER_MODEL",
            "google/gemini-2.5-flash"
        )

        print(f"🌐 Using OpenRouter: {model}")

        return ChatOpenAI(
            api_key=openrouter_key,
            base_url="https://openrouter.ai/api/v1",
            model=model,
            temperature=0,
            max_tokens=8192,
        )

    # =================================================
    # OLLAMA
    # =================================================

    if provider == "ollama":

        model = os.getenv(
            "OLLAMA_MODEL_NAME",
            "llama3.1:latest"
        )

        print(f"🦙 Using Ollama: {model}")

        return ChatOllama(
            model=model,
            base_url=os.getenv(
                "OLLAMA_BASE_URL",
                "http://127.0.0.1:11434"
            ),
            temperature=0,
            num_ctx=8192,
        )

    # =================================================
    # AUTO FALLBACK
    # =================================================

    if os.getenv("GOOGLE_API_KEY"):
        print("🚀 Auto-selected Gemini")

        return ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            google_api_key=os.getenv(
                "GOOGLE_API_KEY"
            ),
            temperature=0,
            max_output_tokens=8192,
        )

    if os.getenv("GROQ_API_KEY"):
        print("⚡ Auto-selected Groq")

        return ChatGroq(
            groq_api_key=os.getenv(
                "GROQ_API_KEY"
            ),
            model_name="llama-3.3-70b-versatile",
            temperature=0,
        )

    if os.getenv("OPENROUTER_API_KEY"):
        print("🌐 Auto-selected OpenRouter")

        return ChatOpenAI(
            api_key=os.getenv(
                "OPENROUTER_API_KEY"
            ),
            base_url="https://openrouter.ai/api/v1",
            model="google/gemini-2.5-flash",
            temperature=0,
            max_tokens=8192,
        )

    raise ValueError(
        "No Gemini, Groq, OpenRouter or Ollama configuration found."
    )
# =====================================================
# TOOLS LIST
# =====================================================

TOOLS = [
    guest_info_tool,
    web_search_tool,
    weather_info_tool,
    hub_stats_tool,
    latest_news_tool,
    youtube_transcript_tool,
    image_info_tool,
    audio_transcriber_tool,
    python_executor_tool,
    excel_reader_tool,
    pdf_reader_tool,
    download_file_tool,
    webpage_reader_tool,
    analyze_file_tool,
    tavily_search_tool,
]

# =====================================================
# LLM
# =====================================================

llm = create_llm()

llm_with_tools = llm.bind_tools(TOOLS)

# =====================================================
# ASSISTANT NODE
# =====================================================

def assistant(state: AgentState):

    messages = state["messages"]

    if not any(
        isinstance(m, SystemMessage)
        for m in messages
    ):
        messages = [
            SystemMessage(content=SYSTEM_PROMPT)
        ] + messages

    config = {}

    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    response = llm_with_tools.invoke(
        messages,
        config=config,
    )

    return {
        "messages": [response]
    }

# =====================================================
# BUILD GRAPH
# =====================================================

def build_agent():

    graph = StateGraph(AgentState)

    graph.add_node(
        "assistant",
        assistant,
    )

    graph.add_node(
        "tools",
        ToolNode(TOOLS),
    )

    graph.add_edge(
        START,
        "assistant",
    )

    graph.add_conditional_edges(
        "assistant",
        tools_condition,
    )

    graph.add_edge(
        "tools",
        "assistant",
    )

    memory = MemorySaver()

    return graph.compile(
        checkpointer=memory
    )

# =====================================================
# INIT AGENT
# =====================================================

agent = build_agent()

# =====================================================
# RUN AGENT
# =====================================================

def run_agent(
    query: str,
    thread_id: str = "default",
):

    result = agent.invoke(
        {
            "messages": [
                HumanMessage(
                    content=query
                )
            ]
        },
        config={
            "configurable": {
                "thread_id": thread_id
            }
        },
    )

    return (
        result["messages"][-1]
        .content
        .strip()
    )

# =====================================================
# FASTAPI ENDPOINT
# =====================================================

@app.post("/answer")
def answer_endpoint(
    request: QuestionRequest,
):

    try:

        answer = run_agent(
            request.question,
            str(uuid.uuid4()),
        )

        return {
            "answer": answer
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )

# =====================================================
# CLI
# =====================================================

if __name__ == "__main__":

    print("\n🎩 GAIA Agent Ready\n")

    thread_id = str(uuid.uuid4())

    while True:

        user_input = input(
            "\nYou: "
        ).strip()

        if user_input.lower() in (
            "exit",
            "quit",
            "bye",
        ):
            break

        try:

            answer = run_agent(
                user_input,
                thread_id,
            )

            print(
                f"\n🎩 Agent:\n{answer}"
            )

        except Exception as e:

            print(
                f"\n❌ Error: {e}"
            )

    print("\n👋 Goodbye!")