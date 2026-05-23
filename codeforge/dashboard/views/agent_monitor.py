"""Agent monitor view: displays live agent status and progress."""

import streamlit as st


def render_agent_monitor():
    st.header("Agent Monitor")

    agents = [
        {"name": "Product Manager", "role": "product_manager",
         "phase": "requirements", "status": "idle", "progress": 0.0},
        {"name": "System Architect", "role": "system_architect",
         "phase": "architecture", "status": "idle", "progress": 0.0},
        {"name": "Code Writer", "role": "code_writer",
         "phase": "implementation", "status": "idle", "progress": 0.0},
        {"name": "Test Engineer", "role": "test_engineer",
         "phase": "testing", "status": "idle", "progress": 0.0},
        {"name": "Code Reviewer", "role": "code_reviewer",
         "phase": "review", "status": "idle", "progress": 0.0},
        {"name": "DevOps", "role": "devops",
         "phase": "deployment", "status": "idle", "progress": 0.0},
    ]

    st.subheader("Status Overview")
    cols = st.columns(6)
    statuses = {"idle": 6, "working": 0, "error": 0, "blocked": 0}
    for i, (status, count) in enumerate(statuses.items()):
        with cols[i]:
            st.metric(status.capitalize(), count)

    st.subheader("Agent Details")
    for agent in agents:
        col1, col2, col3, col4, col5 = st.columns([2, 1, 1, 1, 1])
        with col1:
            st.text(agent["name"])
        with col2:
            st.text(agent["role"])
        with col3:
            color = {"idle": "gray", "working": "green", "error": "red",
                     "blocked": "orange"}.get(agent["status"], "gray")
            st.markdown(f":{color}[{agent['status']}]")
        with col4:
            st.progress(agent["progress"])
        with col5:
            st.text(agent["phase"])
