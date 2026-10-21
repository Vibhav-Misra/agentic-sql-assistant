import os
from typing import Annotated, Literal
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from typing_extensions import TypedDict

from db_tools import list_tables, get_schema, execute_query, generate_chart

load_dotenv()

# 1. Split tools into Safe and Sensitive
safe_tools = [list_tables, get_schema, generate_chart]
sensitive_tools = [execute_query]
all_tools = safe_tools + sensitive_tools

llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools(all_tools)

class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

def chatbot(state: AgentState):
    sys_msg = SystemMessage(content='''You are an expert SQL data analyst. 
    1. Use list_tables and get_schema to understand the data.
    2. Write a SQL query and use execute_query.
    3. If asked for a chart, use generate_chart.
    4. Provide the final answer in plain English.
    ''')
    messages = [sys_msg] + state["messages"]
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 2. Custom Router to distinguish between safe and sensitive tools
def route_tools(state: AgentState) -> Literal["safe_tools", "sensitive_tools", "__end__"]:
    messages = state["messages"]
    last_message = messages[-1]
    
    if not getattr(last_message, "tool_calls", None):
        return END
    
    # If the LLM asked to execute SQL, route to the sensitive node
    if any(tool_call["name"] == "execute_query" for tool_call in last_message.tool_calls):
        return "sensitive_tools"
    
    return "safe_tools"

graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", chatbot)
graph_builder.add_node("safe_tools", ToolNode(safe_tools))
graph_builder.add_node("sensitive_tools", ToolNode(sensitive_tools))

graph_builder.add_edge(START, "agent")
graph_builder.add_conditional_edges("agent", route_tools)
graph_builder.add_edge("safe_tools", "agent")
graph_builder.add_edge("sensitive_tools", "agent")

# 3. Add Memory and the Breakpoint
memory = MemorySaver()
app = graph_builder.compile(
    checkpointer=memory,
    interrupt_before=["sensitive_tools"] # Graph pauses BEFORE executing this node
)