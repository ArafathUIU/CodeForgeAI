"""Streamlit Dashboard for CodeForge.

Provides the main web interface for interacting with the
multi-agent system. Uses PipelineSession directly for state.
"""

from __future__ import annotations

import streamlit as st

from codeforge.api.session import PipelineSession


@st.cache_resource
def get_session() -> PipelineSession:
    return PipelineSession()


def main():
    st.set_page_config(page_title="CodeForge AI", page_icon="🔨", layout="wide")
    st.title("🔨 CodeForge AI")
    st.caption("Multi-Agent Software Development Team")

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

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Phase", state["phase"].capitalize())
    with col2:
        st.metric("Project", state["project_id"][:8] if state["project_id"] else "None")
    with col3:
        st.metric("Messages", state["message_count"])

    phases_list = ["requirements", "architecture", "implementation",
                   "testing", "review", "deployment", "complete"]
    cols = st.columns(len(phases_list))
    current_phase = state["phase"]
    for i, (col, p) in enumerate(zip(cols, phases_list)):
        with col:
            active = p == current_phase
            st.button(
                p[:4].capitalize(),
                key=f"phase_{p}",
                disabled=not active,
                type="primary" if active else "secondary",
                use_container_width=True,
            )

    st.subheader("Start Project")
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
        if st.button("Start Project", type="primary", use_container_width=True):
            if spec.strip():
                with st.spinner("Initializing pipeline..."):
                    result = session.run_sync(spec, output)
                    st.success(f"Project {result['project_id'][:8]} started")
                    st.rerun()
            else:
                st.warning("Enter a specification first")

    if state["errors"]:
        st.error("Errors: " + "; ".join(state["errors"]))


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

    for agent in agents:
        role = agent.get("role", "unknown")
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        with col1:
            st.text(name_map.get(role, role.capitalize()))
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

    tabs = st.tabs(["PRD", "Tech Spec", "Source Code", "Test Suite", "Review", "Deploy"])

    with tabs[0]:
        prd = artifacts.get("prd", {})
        if prd:
            st.subheader(prd.get("title", "Untitled"))
            st.write(prd.get("summary", ""))
            st.json(prd.get("goals", []))
            stories = prd.get("user_stories", [])
            for s in stories[:5]:
                st.caption(s.get("statement", ""))

    with tabs[1]:
        spec = artifacts.get("tech_spec", {})
        if spec:
            st.subheader(spec.get("title", ""))
            st.write(spec.get("overview", ""))
            with st.expander("Tech Stack"):
                for item in spec.get("tech_stack", []):
                    st.text(f"{item.get('category', '')}: {item.get('choice', '')}")

    artifact_keys = [
        "source_code", "test_suite", "review_report", "deployment_config"
    ]
    for i, (tab, key) in enumerate(zip(tabs[2:], artifact_keys)):
        with tab:
            data = artifacts.get(key, {})
            if data:
                st.json(data)
            else:
                st.text(f"No {key} generated yet")


def render_messages(session: PipelineSession):
    st.header("Message Feed")
    state = session.get_state()
    messages = state.get("messages", [])

    st.metric("Total Messages", len(messages))

    type_filter = st.selectbox("Filter", ["All", "task_assignment", "artifact_submission",
                                           "status_update", "approval", "system_event"])
    for msg in reversed(messages[-30:]):
        msg_type = msg.get("type", "unknown")
        if type_filter != "All" and type_filter not in msg_type:
            continue
        with st.container():
            sender = msg.get("sender", "unknown")
            payload = msg.get("payload", {})
            desc = payload.get("description", payload.get("status", str(payload)[:80]))
            st.caption(f"[{msg_type}] {sender}: {desc}")


def render_approvals(session: PipelineSession):
    st.header("Approval Gates")
    state = session.get_state()
    gates = state.get("approval_gates", [])

    if not gates:
        st.info("No pending approvals. Start a project to see approval gates.")

    for gate in gates:
        if gate.get("status") == "resolved":
            continue
        with st.expander(f"Phase: {gate.get('phase', gate.get('id', ''))}"):
            st.text(f"ID: {gate.get('id', '')}")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Approve", key=f"approve_{gate['id']}"):
                    from codeforge.core.message_protocol import Message, MessageType
                    msg = Message(
                        sender="dashboard", recipient="orchestrator",
                        type=MessageType.APPROVAL_RESPONSE,
                        payload={"approval_id": gate["id"], "decision": "approve", "comments": ""},
                    )
                    import asyncio
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(session._orchestrator._message_bus.publish(msg))
                    loop.close()
                    st.rerun()
            with col2:
                if st.button("Reject", key=f"reject_{gate['id']}"):
                    from codeforge.core.message_protocol import Message, MessageType
                    msg = Message(
                        sender="dashboard", recipient="orchestrator",
                        type=MessageType.APPROVAL_RESPONSE,
                        payload={"approval_id": gate["id"], "decision": "reject", "comments": ""},
                    )
                    import asyncio
                    loop = asyncio.new_event_loop()
                    loop.run_until_complete(session._orchestrator._message_bus.publish(msg))
                    loop.close()
                    st.rerun()


if __name__ == "__main__":
    main()
