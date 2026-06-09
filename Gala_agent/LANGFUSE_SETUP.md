# Langfuse Integration Setup Guide

Langfuse has been integrated into the Gala agent for comprehensive observability and tracing of LLM interactions. This guide will help you set up and use Langfuse with your Gala agent.

## What is Langfuse?

Langfuse is an open-source observability platform for LLM applications. It captures:
- All LLM calls with inputs/outputs
- Token usage and costs
- Tool invocations
- Full execution traces
- Performance metrics and latencies
- Agent decision flows in LangGraph

## Setup Steps

### 1. Create a Langfuse Account

1. Go to [https://cloud.langfuse.com](https://cloud.langfuse.com)
2. Sign up for a free account
3. Create a new project

### 2. Get Your API Keys

1. Go to **Settings → API Keys** in your Langfuse project
2. Copy your **Public Key** (pk-lf-...)
3. Copy your **Secret Key** (sk-lf-...)

### 3. Update Your `.env` File

Edit `.env` in the `Gala_agent` directory and replace the placeholder values:

```bash
export LANGFUSE_PUBLIC_KEY="pk-lf-YOUR_PUBLIC_KEY"
export LANGFUSE_SECRET_KEY="sk-lf-YOUR_SECRET_KEY"
export LANGFUSE_BASE_URL="https://cloud.langfuse.com"
```

**Note:** If you're using a self-hosted Langfuse instance, update the `LANGFUSE_BASE_URL` accordingly.

### 4. Run the Agent

Run the agent as usual:

```bash
python app.py
```

When prompted, enter your user ID (e.g., `user-123`). This will be used as the session ID for grouping conversations.

## What Gets Traced

Once enabled, the following data is automatically captured:

- **User queries and agent responses**
- **LLM model name** (Qwen2.5-Coder-32B-Instruct)
- **Token usage** (input/output tokens)
- **Tool invocations** (all 5 tools: guest_info, web_search, weather_info, hub_stats, latest_news)
- **Execution time and latencies**
- **Session and user information**

## Viewing Traces

1. After running the agent with queries, go to your Langfuse project dashboard
2. Click on **Traces** to see all recorded interactions
3. Click on any trace to see:
   - Full conversation flow
   - Tool calls and their results
   - Token usage and costs
   - Execution timeline
   - LLM model parameters

## Key Features

### Sessions
- All messages from the same user session are grouped together
- Use the **Sessions** view to track full conversations
- Useful for debugging multi-turn interactions

### Spans and Hierarchy
- Each tool invocation is captured as a separate span
- Agent decisions are shown in the execution flow
- Nested structure shows which tools were called and when

### Analytics
- View token costs per user
- Track performance metrics over time
- Filter by user, session, or tags
- Build custom dashboards

## Optional: Add Custom Tags

You can enhance tracing by adding custom tags for better filtering:

```python
# In app.py, modify the langfuse_handler initialization:
langfuse_handler = CallbackHandler(
    session_id=user_id,
    tags=["gala-agent", "production"]  # Add tags
)
```

## Troubleshooting

### Traces Not Appearing?
1. Verify your API keys are correct in `.env`
2. Check that `LANGFUSE_BASE_URL` matches your Langfuse region
3. Run with a Langfuse-aware query (requires LLM invocation)
4. Check the console for any error messages

### Optional: Disable Langfuse
If you want to temporarily disable Langfuse tracing, leave `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` empty in `.env`. The agent will still work without errors.

## Documentation

For more information, see:
- [Langfuse Documentation](https://langfuse.com/docs)
- [LangChain Integration Guide](https://langfuse.com/docs/integrations/langchain)
- [LangGraph Integration Guide](https://langfuse.com/docs/integrations/langgraph)

## Architecture

The integration uses:
- **Langfuse SDK** (v3+) - For core tracing functionality
- **LangChain CallbackHandler** - Automatic integration with LLM calls and tools
- **LangGraph** - Automatically captured through LangChain callbacks

All interactions are automatically captured without requiring code changes to your agent logic.
