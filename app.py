import streamlit as st
from langchain_core.messages import HumanMessage
from agent import app

# Clean, professional page configuration
st.set_page_config(page_title="Data Operations Terminal", layout="centered")

st.title("Data Operations")
st.caption("Natural Language to SQL Execution Interface")
st.divider()

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_query = st.chat_input("Enter your query (e.g., What was the total revenue in the West region?)")

if user_query:
    with st.chat_message("user"):
        st.markdown(user_query)
    st.session_state.messages.append({"role": "user", "content": user_query})

    with st.chat_message("assistant"):
        # Professionalized system log
        with st.status("Executing operational workflow...", expanded=True) as status:
            events = app.stream(
                {"messages": [HumanMessage(content=user_query)]}, 
                stream_mode="values"
            )
            
            final_answer = ""
            for event in events:
                if "messages" in event:
                    latest_msg = event["messages"][-1]
                    
                    if latest_msg.type == "ai" and getattr(latest_msg, 'tool_calls', None):
                        tool_names = [t['name'] for t in latest_msg.tool_calls]
                        # Rendered as a system audit log
                        st.code(f"System Action: Invoking {', '.join(tool_names)}", language="bash")
                    
                    elif latest_msg.type == "ai" and not getattr(latest_msg, 'tool_calls', None):
                        final_answer = latest_msg.content
                        
            status.update(label="Query execution complete", state="complete", expanded=False)
        
        st.markdown(final_answer)
        st.session_state.messages.append({"role": "assistant", "content": final_answer})