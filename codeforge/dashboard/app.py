"""Streamlit Dashboard for CodeForge.

Provides the main web interface for interacting with the
multi-agent system. Uses PipelineSession directly for state.
"""

from __future__ import annotations

import streamlit as st

from codeforge.api.session import PipelineSession

PHASES_LIST = [
    "requirements", "architecture", "implementation",
    "testing", "review", "deployment", "complete",
]


@st.cache_resource
def get_session() -> PipelineSession:
    return PipelineSession()


def main():
    st.set_page_config(page_title="CodeForge AI", page_icon="🔨", layout="wide")
    st.title("🔨 CodeForge AI")
    st.caption("Multi-Agent AI Software Development System")

    session = get_session()

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Pipeline", "Agents", "Artifacts", "Messages", "Approvals",
    ])

    with tab1:
        render_pipeline(session)

    with tab2:
        render_agent_monitor(session)

    with tab3:
        render_artifacts(session)

    with tab4:
        render_messages(session)

    with tab5:
        render_approvals(session)


def render_pipeline(session: PipelineSession):
    st.header("Pipeline Control")
    state = session.get_state()

    col1, col2, col3, col4 = st.columns(4)
    current_phase = state["phase"]
    with col1:
        st.metric("Phase", current_phase.capitalize())
    with col2:
        pid = state["project_id"]
        st.metric("Project", pid[:8] if pid else "—")
    with col3:
        st.metric("Messages", state["message_count"])
    with col4:
        st.metric("Artifacts", len(state.get("artifacts", {})))

    st.subheader("Phase Progress")
    current_idx = PHASES_LIST.index(current_phase) if current_phase in PHASES_LIST else -1
    cols = st.columns(len(PHASES_LIST))
    for i, (col, p) in enumerate(zip(cols, PHASES_LIST)):
        with col:
            if i < current_idx:
                label = f"✅ {p[:4].capitalize()}"
                btype = "secondary"
            elif i == current_idx:
                label = f"▶ {p[:4].capitalize()}"
                btype = "primary"
            else:
                label = f"◻ {p[:4].capitalize()}"
                btype = "secondary"
            st.button(label, key=f"phase_{p}", disabled=True, type=btype,
                      use_container_width=True)

    st.subheader("Start New Project")
    col1, col2 = st.columns([3, 1])
    with col1:
        spec = st.text_area(
            "Specification",
            key="spec_input",
            placeholder=(
                "Describe your app: e.g., 'Build a todo app with "
                "user auth, CRUD tasks, data export, and a dashboard'"
            ),
            height=100,
        )
    with col2:
        output = st.text_input("Output Dir", value=".codeforge/output", key="output_dir")
        if st.button("▶ Run Pipeline", type="primary", use_container_width=True):
            if spec.strip():
                with st.spinner("Running full pipeline (all 6 agents)..."):
                    result = session.run_sync(spec, output)
                    st.success(f"Phase: {result['phase']} | "
                               f"Artifacts: {list(result['artifacts'].keys())}")
                    st.rerun()
            else:
                st.warning("Enter a specification first")

    if state["errors"]:
        st.error("Errors: " + "; ".join(state["errors"]))
    elif current_phase == "complete":
        st.success("Pipeline completed successfully — all 6 artifacts produced")
    elif current_phase == "failed":
        st.error("Pipeline failed")


def render_agent_monitor(session: PipelineSession):
    st.header("Agent Monitor")
    state = session.get_state()
    agents = state.get("agents", [])

    if not agents:
        _role_idle = {"state": "idle", "progress": 0.0}
        agents = [
            {"agent_id": "product_manager", "role": "product_manager", **_role_idle},
            {"agent_id": "system_architect", "role": "system_architect", **_role_idle},
            {"agent_id": "code_writer", "role": "code_writer", **_role_idle},
            {"agent_id": "test_engineer", "role": "test_engineer", **_role_idle},
            {"agent_id": "code_reviewer", "role": "code_reviewer", **_role_idle},
            {"agent_id": "devops", "role": "devops", **_role_idle},
        ]

    name_map = {
        "product_manager": "Product Manager",
        "system_architect": "System Architect",
        "code_writer": "Code Writer",
        "test_engineer": "Test Engineer",
        "code_reviewer": "Code Reviewer",
        "devops": "DevOps",
    }

    phase_agents = {
        "requirements": "product_manager",
        "architecture": "system_architect",
        "implementation": "code_writer",
        "testing": "test_engineer",
        "review": "code_reviewer",
        "deployment": "devops",
    }
    current_phase = state["phase"]
    current_agent = phase_agents.get(current_phase)

    for agent in agents:
        role = agent.get("role", "unknown")
        is_current = role == current_agent
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            prefix = "▶ " if is_current else "  "
            st.text(f"{prefix}{name_map.get(role, role.capitalize())}")
        with col2:
            ag_state = agent.get("state", "idle")
            color = {"idle": "gray", "working": "green", "blocked": "orange",
                     "error": "red"}.get(ag_state, "gray")
            st.markdown(f":{color}[{ag_state}]")
        with col3:
            st.progress(agent.get("progress", 0.0))
        with col4:
            task = agent.get("current_task")
            if task:
                st.caption(task[:40])


def render_artifacts(session: PipelineSession):
    st.header("Artifact Viewer")
    state = session.get_state()
    artifacts = state.get("artifacts", {})

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    labels = ["PRD", "Tech Spec", "Source", "Tests", "Review", "Deploy"]
    keys = ["prd", "tech_spec", "source_code", "test_suite", "review_report", "deployment_config"]
    for col, label, key in zip([col1, col2, col3, col4, col5, col6], labels, keys):
        with col:
            present = key in artifacts
            color = "green" if present else "gray"
            st.markdown(f":{color}_circle: {label}")

    tab_labels = ["PRD", "Tech Spec", "Source Code", "Test Suite", "Review Report", "Deploy Config"]
    tabs = st.tabs(tab_labels)

    def _show_prd(data):
        if not data:
            st.info("Not yet generated")
            return
        st.subheader(data.get("title", "Untitled"))
        st.write(data.get("summary", ""))
        st.subheader("Goals")
        st.json(data.get("goals", []))
        stories = data.get("user_stories", [])
        if stories:
            st.subheader("User Stories")
            for i, s in enumerate(stories[:10]):
                st.caption(f"{i+1}. {s.get('statement', str(s))}")

    def _show_techspec(data):
        if not data:
            st.info("Not yet generated")
            return
        st.subheader(data.get("title", ""))
        st.write(data.get("overview", ""))
        with st.expander("Tech Stack"):
            for item in data.get("tech_stack", []):
                st.text(f"{item.get('category', '')}: {item.get('choice', '')}")
        with st.expander("API Contracts"):
            st.json(data.get("api_contracts", []))
        with st.expander("File Tree"):
            st.json(data.get("file_tree", {}))
        with st.expander("Full Tech Spec JSON"):
            st.json(data)

    def _show_generic(data, label):
        if not data:
            st.info(f"No {label.lower()} generated yet")
            return
        if isinstance(data, dict):
            for key, val in data.items():
                with st.expander(f"{label}: {key}"):
                    if isinstance(val, (dict, list)):
                        st.json(val)
                    else:
                        st.write(str(val)[:2000])
        elif isinstance(data, list):
            st.json(data)
        else:
            st.write(str(data)[:2000])

    with tabs[0]:
        _show_prd(artifacts.get("prd", {}))
    with tabs[1]:
        _show_techspec(artifacts.get("tech_spec", {}))
    with tabs[2]:
        _show_generic(artifacts.get("source_code", {}), "Source")
    with tabs[3]:
        _show_generic(artifacts.get("test_suite", {}), "Tests")
    with tabs[4]:
        _show_generic(artifacts.get("review_report", {}), "Review")
    with tabs[5]:
        _show_generic(artifacts.get("deployment_config", {}), "Deploy")


def render_messages(session: PipelineSession):
    st.header("Message Feed")
    state = session.get_state()
    messages = state.get("messages", [])

    st.metric("Total Messages", len(messages))

    type_filter = st.selectbox(
        "Filter", ["All", "task_assignment", "artifact_submission",
                   "status_update", "approval", "system_event"],
    )

    if not messages:
        st.info("No messages yet. Start a project first.")
        return

    for msg in reversed(messages[-40:]):
        msg_type = msg.get("type", "unknown")
        if type_filter != "All" and type_filter not in msg_type:
            continue
        with st.container():
            sender = msg.get("sender", "unknown")
            recipient = msg.get("recipient", "")
            payload = msg.get("payload", {})
            desc = payload.get("description", payload.get("status", str(payload)[:80]))
            st.caption(f"[{msg_type}] {sender} → {recipient}: {desc}")


def render_approvals(session: PipelineSession):
    st.header("Approval Gates")
    state = session.get_state()
    gates = state.get("approval_gates", [])

    pending = [g for g in gates if g.get("status") != "resolved"]
    resolved = [g for g in gates if g.get("status") == "resolved"]

    col1, col2 = st.columns(2)
    with col1:
        st.metric("Pending", len(pending))
    with col2:
        st.metric("Resolved", len(resolved))

    if not gates:
        st.info("No approval gates yet. Start a project and gates appear at each gated phase.")
        return

    for gate in reversed(gates):
        status = gate.get("status", "unknown")
        icon = "✅" if status == "resolved" else "⏳"
        with st.expander(
            f"{icon} {gate.get('phase', gate.get('id', ''))}"
            f" — {gate.get('decision', status)}"
        ):
            st.text(f"ID: {gate.get('id', '')}")
            st.text(f"Artifact: {gate.get('artifact_id', '')}")
            st.text(f"Description: {gate.get('description', '')}")

            if status != "resolved":
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Approve", key=f"approve_{gate['id']}"):
                        _send_approval(session, gate["id"], "approve")
                with col2:
                    if st.button("Reject", key=f"reject_{gate['id']}"):
                        _send_approval(session, gate["id"], "reject")


def _send_approval(session: PipelineSession, gate_id: str, decision: str) -> None:
    import asyncio

    from codeforge.core.message_protocol import Message, MessageType

    msg = Message(
        sender="dashboard",
        recipient="orchestrator",
        type=MessageType.APPROVAL_RESPONSE,
        payload={"approval_id": gate_id, "decision": decision, "comments": ""},
    )
    loop = asyncio.new_event_loop()
    try:
        loop.run_until_complete(session._orchestrator._message_bus.publish(msg))
    finally:
        loop.close()
    st.rerun()


if __name__ == "__main__":
    main()
