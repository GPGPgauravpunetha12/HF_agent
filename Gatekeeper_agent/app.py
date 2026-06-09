import io
import os
from typing import TypedDict, List, Dict, Any, Optional
from IPython.display import Image, display
from PIL import Image as PILImage
from langfuse import get_client, observe
from langfuse.langchain import CallbackHandler
from langgraph.graph import StateGraph, START, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# Securely load your API key from environment variables (Recommended)
# FIXED: Removed the floating bare string key to fix syntax crashing
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Tracing / Langfuse configuration
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "")
os.environ["LANGFUSE_BASE_URL"] = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

# Initialize LLM using OpenRouter - FIXED: Switched to the universal free model router
model = ChatOpenAI(
    model="openrouter/free",
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    temperature=0
)

# Initialize Langfuse tracing client
langfuse_client = get_client()

# Initialize Langfuse callback handler for LangGraph/LangChain tracing
langfuse_handler = CallbackHandler()

# State declaration
class EmailState(TypedDict):
    email: Dict[str, Any]
    is_spam: Optional[bool]
    spam_reason: Optional[str]
    email_draft: Optional[str]
    email_category: Optional[str]
    messages: List[Dict[str, Any]]

@observe(name="read_email", as_type="span")
def read_email(state: EmailState):
    email = state["email"]
    print(f"\nJarvis is processing an email from {email['sender']} with subject: {email['subject']}\n")
    return {"email": email, "messages": []}

@observe(name="classify_email", as_type="generation")
def classify_email(state: EmailState):
    email = state["email"]

    system_prompt = f"""
As Jarvis the butler of Mr Gaurav and his SECRET identity Joker, analyze this email and determine if it is spam or legitimate and should be brought to Mr Gaurav's attention.

Email:
From: {email['sender']}
Subject: {email['subject']}
Body: {email['body']}

First, determine if this email is spam.
Answer with SPAM or HAM if it's legitimate. Only return the answer.
Answer:
"""
    messages = [HumanMessage(content=system_prompt)]
    response = model.invoke(messages)

    response_text = response.content.lower()
    print(f"Classification Result: {response_text.strip()}")
    is_spam = "spam" in response_text and "ham" not in response_text

    if not is_spam:
        new_messages = state.get("messages", []) + [
            {"role": "user", "content": system_prompt},
            {"role": "assistant", "content": response.content}
        ]
    else:
        new_messages = state.get("messages", [])

    return {
        "is_spam": is_spam,
        "messages": new_messages
    }

@observe(name="handle_spam", as_type="span")
def handle_spam(state: EmailState):
    print("Jarvis has marked this email as spam.")
    print("The email has been moved to the spam folder.")
    return {"email_category": "spam"}

@observe(name="draft_response", as_type="generation")
def drafting_response(state: EmailState):
    email = state["email"]

    reply_prompt = f"""As Jarvis the butler, draft a preliminary response to this email.
Email:
From: {email['sender']}
Subject: {email['subject']}
Body: {email['body']}

Draft a brief preliminary response that Mr. Gaurav can review and personalize before sending.
"""
    messages = [HumanMessage(content=reply_prompt)]
    response = model.invoke(messages)

    new_messages = state.get('messages', []) + [
        {"role": "user", "content": reply_prompt},
        {"role": "assistant", "content": response.content}
    ]
    return {
        "email_draft": response.content,
        "messages": new_messages
    }

@observe(name="notify_mr_gaurav", as_type="span")
def notify_mr_gaurav(state: EmailState):
    print("\n" + "=" * 50)
    print(f"Sir, you have received an email from {state['email']['sender']}.")
    print(f"Subject: {state['email']['subject']}")
    print("I have prepared a draft response for your review:")
    print("-" * 50)
    print(state["email_draft"])
    print("=" * 50 + "\n")
    return {"email_category": "legitimate"}

# Define routing logic
def route_email(state: EmailState):
    if state["is_spam"]:
        return "spam"
    else:
        return "legitimate"

# Create the graph
email_graph = StateGraph(EmailState)

# Nodes mapping
email_graph.add_node("read_email", read_email)
email_graph.add_node("classify_email", classify_email)
email_graph.add_node("handle_spam", handle_spam)
email_graph.add_node("draft_response", drafting_response)
email_graph.add_node("notify_mr_gaurav", notify_mr_gaurav)

# Edges mapping
email_graph.add_edge(START, "read_email")
email_graph.add_edge("read_email", "classify_email")
email_graph.add_conditional_edges(
    "classify_email",
    route_email,
    {
        "spam": "handle_spam",
        "legitimate": "draft_response"
    }
)
email_graph.add_edge("handle_spam", END)
email_graph.add_edge("draft_response", "notify_mr_gaurav")
email_graph.add_edge("notify_mr_gaurav", END)

# Compile graph
compile_graph = email_graph.compile()

# Optional visual layout generator
try:
    img = Image(compile_graph.get_graph().draw_mermaid_png())
    image_bytes = img.data
    image = PILImage.open(io.BytesIO(image_bytes))
    image.show()
except Exception:
    print("Graph compiled successfully (Visual rendering skipped; requires optional local system tools).")

# Example email datasets for validation
legitimate_email_data = {
    "sender": "Speed",
    "subject": "Found you Joker",
    "body": "Mr. Gaurav, I found your secret identity! I know you're Joker! There's no denying it, I have proof and I am coming to find you soon!"
}

spam_email_data = {
    "sender": "Crypto bro",
    "subject": "The best investment of 2025",
    "body": "Mr Gaurav, I just launched an ALT coin and want you to buy some!"
}

# Run legitimate test pipeline
print("--- RUNNING LEGITIMATE TEST ---")
compile_graph.invoke(
    {
        "email": legitimate_email_data,
        "is_spam": None,
        "email_category": None,
        "email_draft": None,
        "messages": []
    },
    config={"callbacks": [langfuse_handler]}
)

# Run spam test pipeline
print("--- RUNNING SPAM TEST ---")
compile_graph.invoke(
    {
        "email": spam_email_data,
        "is_spam": None,
        "email_category": None,
        "email_draft": None,
        "messages": []
    },
    config={"callbacks": [langfuse_handler]}
)
