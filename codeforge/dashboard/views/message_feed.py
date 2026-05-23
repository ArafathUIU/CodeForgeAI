"""Message feed view: real-time message bus display."""

import streamlit as st


def render_message_feed():
    st.header("Message Feed")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.selectbox(
            "Filter by Type",
            ["All", "Task", "Artifact", "Status", "Approval", "System"],
            key="msg_type_filter",
        )
    with col2:
        st.selectbox(
            "Filter by Agent",
            ["All", "PM", "Architect", "Code Writer", "Tester", "Reviewer", "DevOps"],
            key="msg_agent_filter",
        )
    with col3:
        st.metric("Messages", "0")

    st.subheader("Recent Messages")
    samples = [
        {"type": "System", "from": "Orchestrator", "msg": "Pipeline started"},
        {"type": "Task", "from": "Orchestrator", "msg": "Assign PM task"},
        {"type": "Status", "from": "Product Manager", "msg": "Generating PRD"},
    ]
    for msg in samples:
        with st.container():
            st.caption(f"[{msg['type']}] {msg['from']}: {msg['msg']}")
