import os
import streamlit as st
import json
from langchain_core.messages import HumanMessage
from agent import app

st.set_page_config(page_title="Data Operations Terminal", layout="centered")
st.title("Data Operations")
st.caption("Natural Language to SQL & Visualization Interface")

with st.expander("System Capabilities & Available Tools"):
    st.markdown("""
    This agent uses a cyclical reasoning loop (LangGraph) to safely retrieve and analyze data:
    * **`list_tables`**: Scans the database metadata.
    * **`get_schema`**: Inspects specific table columns.
    * **`execute_query`**: (REQUIRES APPROVAL) Executes read-only queries.
    * **`generate_chart`**: Generates matplotlib visualizations.
    """)
st.divider()

# Session State Initialization
if "messages" not in st.session_state:
    st.session_state.messages = []
# We need a unique thread ID for LangGraph memory
if "thread_id" not in st.session_state:
    st.session_state.thread_id = "1"

config = {"configurable": {"thread_id": st.session_state.thread_id}}

# Render existing chat history
for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        if "content" in msg and msg["content"]:
            st.markdown(msg["content"])
        if "image" in msg and msg["image"]:
            st.image(msg["image"])
        # NEW: Render the download button if CSV data exists
        if "csv" in msg and msg["csv"]:
            st.download_button(
                label="📥 Download Data (CSV)",
                data=msg["csv"],
                file_name="query_results.csv",
                mime="text/csv",
                key=f"dl_btn_{i}"
            )

# --- CORE EXECUTION FUNCTION ---
def run_agent(input_data=None):
    with st.chat_message("assistant"):
        with st.status("Executing operational workflow...", expanded=True) as status:
            # If input_data is None, we are resuming a paused graph. 
            # If it has content, it's a new user message.
            events = app.stream(input_data, config, stream_mode="values")
            
            final_answer = ""
            for event in events:
                if "messages" in event:
                    latest_msg = event["messages"][-1]
                    
                    if latest_msg.type == "ai" and getattr(latest_msg, 'tool_calls', None):
                        tool_names = [t['name'] for t in latest_msg.tool_calls]
                        st.code(f"System Action: Invoking {', '.join(tool_names)}", language="bash")
                    
                    elif latest_msg.type == "ai" and not getattr(latest_msg, 'tool_calls', None):
                        final_answer = latest_msg.content
                        
            status.update(label="Query execution complete", state="complete", expanded=False)
        
        # Check if the graph paused (meaning it's waiting for approval)
        current_state = app.get_state(config)
        if current_state.next and current_state.next[0] == "sensitive_tools":
            st.warning("⚠️ **Approval Required: Database Execution Intercepted**")
            # Extract the drafted SQL query to show the user
            last_msg = current_state.values["messages"][-1]
            drafted_sql = json.loads(last_msg.tool_calls[0]["args"]["query"]) if isinstance(last_msg.tool_calls[0]["args"], str) else last_msg.tool_calls[0]["args"].get("query", "")
            
            st.code(drafted_sql, language="sql")
            st.session_state.awaiting_approval = True
            st.rerun() # Refresh UI to show the approval buttons

        # If it didn't pause, the answer is final.
        elif final_answer:
            st.markdown(final_answer)
            
            # Check for generated chart
            img_bytes = None
            if os.path.exists("output_chart.png"):
                st.image("output_chart.png")
                with open("output_chart.png", "rb") as f:
                    img_bytes = f.read()
                os.remove("output_chart.png")
                
            # NEW: Check for generated CSV data
            csv_data = None
            if os.path.exists("results.csv"):
                with open("results.csv", "rb") as f:
                    csv_data = f.read()
                os.remove("results.csv")
                
                # Render the download button for the current message
                st.download_button(
                    label="Download Data (CSV)",
                    data=csv_data,
                    file_name="query_results.csv",
                    mime="text/csv",
                    key=f"dl_btn_current_{len(st.session_state.messages)}"
                )
                
            # Save everything to the chat history
            st.session_state.messages.append({
                "role": "assistant", 
                "content": final_answer, 
                "image": img_bytes,
                "csv": csv_data
            })

# --- APPROVAL UI BLOCK ---
if getattr(st.session_state, "awaiting_approval", False):
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Approve & Execute SQL", use_container_width=True):
            st.session_state.awaiting_approval = False
            # Passing 'None' to a paused graph tells it to resume from where it left off
            run_agent(None) 
            st.rerun()
    with col2:
        if st.button("❌ Reject Query", type="primary", use_container_width=True):
            st.session_state.awaiting_approval = False
            st.error("Query rejected. Please ask a new question.")
            st.stop()

# --- USER INPUT LOGIC ---
# Only show the chat input if we aren't currently waiting for an approval
elif user_query := st.chat_input("Enter your query..."):
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})
    run_agent({"messages": [HumanMessage(content=user_query)]})