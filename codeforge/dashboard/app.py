"""Streamlit Dashboard for CodeForge.

Provides the main web interface for interacting with the
multi-agent system: monitoring agents, viewing artifacts,
managing approvals, and watching the message feed.
"""

import streamlit as st
from codeforge.dashboard.views import (
    render_agent_monitor,
    render_artifact_viewer,
    render_approval_gate,
    render_message_feed,
    render_pipeline_status,
)

st.set_page_config(
    page_title="CodeForge AI",
    page_icon="🔨",
    layout="wide",
)

st.title("🔨 CodeForge AI")
st.caption("Multi-Agent Software Development Team")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Pipeline",
    "Agents",
    "Artifacts",
    "Messages",
    "Approvals",
])

with tab1:
    render_pipeline_status()

with tab2:
    render_agent_monitor()

with tab3:
    render_artifact_viewer()

with tab4:
    render_message_feed()

with tab5:
    render_approval_gate()
