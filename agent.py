import os
from typing import Annotated
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from typing_extensions import TypedDict

# Import the database tools we built in Phase 2
from db_tools import list_tables, get_schema, execute_query

# Load the API key from the .env file
load_dotenv()

# 1. Define the Tools and the LLM
tools = [list_tables, get_schema, execute_query]
# We use temperature=0 because we want deterministic, factual SQL generation, not creative writing.
llm = ChatOpenAI(model="gpt-4o", temperature=0)
llm_with_tools = llm.bind_tools(tools)

# 2. Define the State
# The State tracks the conversation history. 'add_messages' ensures new 
# messages are appended to the list rather than overwriting it.
class AgentState(TypedDict):
    messages: Annotated[list, add_messages]

# 3. Define the LLM Node
def chatbot(state: AgentState):
    """The main brain of the agent."""
    sys_msg = SystemMessage(content='''You are an expert SQL data analyst. 
    When asked a question, follow these exact steps:
    1. Use list_tables to see available tables.
    2. Use get_schema to understand the structure of the relevant tables.
    3. Write and execute a SQL query using execute_query.
    4. If the query fails, read the error message, rewrite the SQL, and try again.
    5. Finally, answer the user's question in plain English based on the data.
    ''')
    
    # Prepend the system instructions to the conversation history
    messages = [sys_msg] + state["messages"]
    
    # Call the LLM
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}

# 4. Build the Graph
graph_builder = StateGraph(AgentState)

# Add the nodes (the actors)
graph_builder.add_node("agent", chatbot)
graph_builder.add_node("tools", ToolNode(tools)) # ToolNode runs the python functions

# Add the edges (the routing logic)
graph_builder.add_edge(START, "agent")

# tools_condition checks the LLM's output: 
# If it asked to use a tool, route to "tools". If it wrote a normal text response, route to END.
graph_builder.add_conditional_edges("agent", tools_condition)

# After the tools finish running, always route back to the agent to evaluate the results
graph_builder.add_edge("tools", "agent")

# Compile the final graph into an executable application
app = graph_builder.compile()

# --- Test block ---
if __name__ == "__main__":
    print("Agent is ready! Ask a question (type 'quit' to exit).")
    while True:
        user_input = input("\nUser: ")
        if user_input.lower() in ["quit", "exit", "q"]:
            break
            
        # Stream the agent's thought process
        events = app.stream(
            {"messages": [HumanMessage(content=user_input)]}, 
            stream_mode="values"
        )
        
        for event in events:
            if "messages" in event:
                latest_msg = event["messages"][-1]
                
                # If the agent is using a tool, print a status update
                if latest_msg.type == "ai" and latest_msg.tool_calls:
                    tool_names = [t['name'] for t in latest_msg.tool_calls]
                    print(f"   [Agent is thinking... using tools: {', '.join(tool_names)}]")
                
                # If the agent responds with final text, print it
                elif latest_msg.type == "ai" and not latest_msg.tool_calls:
                    print(f"\nAgent: {latest_msg.content}")