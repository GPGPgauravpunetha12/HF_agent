import os
import base64
from typing import List, TypedDict, Annotated, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import AnyMessage, SystemMessage, HumanMessage
from langgraph.graph.message import add_messages
from langgraph.graph import START, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from IPython.display import Image, display
from langfuse import get_client, observe
from langfuse.langchain import CallbackHandler

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Tracing / Langfuse configuration
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "")
os.environ["LANGFUSE_BASE_URL"] = os.getenv("LANGFUSE_BASE_URL", "https://cloud.langfuse.com")

# Initialize Langfuse tracing client
langfuse_client = get_client()

# Initialize Langfuse callback handler for LangGraph/LangChain tracing
langfuse_handler = CallbackHandler()

vision_llm= ChatOpenAI(
    model="meta-llama/llama-3.3-70b-instruct:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    temperature=0
)
class AgentState(TypedDict):
    # The document provided
    input_file: Optional[str]  # Contains file path (PDF/PNG)
    messages: Annotated[list[AnyMessage], add_messages]

@observe(name="extract_text", as_type="generation")
def extract_text(img_path:str)->str:
    """Extract text from img file using multimodel model
    Master Gaurav often leaves notes with his training regime or meal plans
    this allows me to properly annalyse the plans"""
    all_text=""
    try:
        with open(img_path,"rb")as f:
            img_bytes=f.read()
        img_base64=base64.b64encode(img_bytes).decode("utf-8")

        # prepare the prompt including base64 data
        message=[
            HumanMessage(content=[{
                "type":"text",
                "text":(
                    "Extract all text from this image. "
                    "Return only the extracted text, no explanations."
                ),
            },{
                "type":"img_url",
                "img_url":{
                    "url":f"data:image/png;base64,{img_base64}"
                }
            }])
        ]
        
        # call the vision-capable model
        response=vision_llm.invoke(message)
        # append extracted text
        all_text+=response.content+"\n\n"
        return all_text.strip()
    except Exception as e:
        error_msg=f"Error extracting text{str(e)}"
        print(error_msg)
        return ""
    
@observe(name="divide", as_type="span")
def divide(a:int,b:int)->float:
    """Divide a and b - for Master Gaurav's occasional calculations."""
    return a / b


# equp the butler with tools
tools={
    extract_text,
    divide
}
llm=ChatOpenAI(
    model="meta-llama/llama-3.3-70b-instruct:free",
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    temperature=0
)
llm_with_tools=llm.bind_tools(tools, parallel_tool_calls=False)

@observe(name="assistant", as_type="span")
def assistant(state: AgentState):
    # System message
    textual_description_of_tool="""
extract_text(img_path: str) -> str:
    Extract text from an image file using a multimodal model.

    Args:
        img_path: A local image file path (strings).

    Returns:
        A single string containing the concatenated text extracted from each image.
divide(a: int, b: int) -> float:
    Divide a and b
"""
    image=state["input_file"]
    sys_msg = SystemMessage(content=f"You are a helpful butler named Jarvis that serves Mr. Gaurav and Joker. You can analyse documents and run computations with provided tools:\n{textual_description_of_tool} \n You have access to some optional images. Currently the loaded image is: {image}")

    return {
        "messages": [llm_with_tools.invoke([sys_msg] + state["messages"])],
        "input_file": state["input_file"]
    }
    
# The graph
builder = StateGraph(AgentState)

# Define nodes: these do the work
builder.add_node("assistant", assistant)
builder.add_node("tools", ToolNode(tools))

# Define edges: these determine how the control flow moves
builder.add_edge(START, "assistant")
builder.add_conditional_edges(
    "assistant",
    # If the latest message requires a tool, route to tools
    # Otherwise, provide a direct response
    tools_condition,
)
builder.add_edge("tools", "assistant")
react_graph = builder.compile()



# Show the butler's thought process
display(Image(react_graph.get_graph(xray=True).draw_mermaid_png()))
# messages = [HumanMessage(content="Divide 6790 by 5")]
# messages = react_graph.invoke(
#     {"messages": messages, "input_file": None},
#     config={"callbacks": [langfuse_handler]}
# )
# Show the messages



messages = [HumanMessage(content="According the note provided by MR gaurav in the provided images. what is  his training program for the week?")]

messages = react_graph.invoke({"messages": messages, "input_file": "Capture.PNG"})


for m in messages['messages']:
    m.pretty_print()
