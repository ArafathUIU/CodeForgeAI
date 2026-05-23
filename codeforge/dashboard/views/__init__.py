"""Dashboard view modules for the Streamlit interface.

Each module renders a section of the dashboard:
- agent_monitor: Live agent status and progress
- artifact_viewer: PRD, TechSpec, and code browser
- approval_gate: Human-in-the-loop approval interface
- message_feed: Real-time message bus display
- pipeline_status: Pipeline phase and progress overview
"""

from codeforge.dashboard.views.agent_monitor import render_agent_monitor
from codeforge.dashboard.views.artifact_viewer import render_artifact_viewer
from codeforge.dashboard.views.approval_gate import render_approval_gate
from codeforge.dashboard.views.message_feed import render_message_feed
from codeforge.dashboard.views.pipeline_status import render_pipeline_status

__all__ = [
    "render_agent_monitor",
    "render_artifact_viewer",
    "render_approval_gate",
    "render_message_feed",
    "render_pipeline_status",
]
