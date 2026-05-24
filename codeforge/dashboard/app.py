"""Streamlit Dashboard for CodeForge — Tech Command Center.

Agent conversation feed, decision board, pipeline map, artifact explorer.
"""

from __future__ import annotations

import streamlit as st

from codeforge.api.session import PipelineSession

PHASES_LIST = [
    "requirements", "architecture", "implementation",
    "testing", "review", "deployment", "complete",
]

CSS = """
<style>
/* Dark tech theme */
.main { background: #0a0e17; }
.stApp { background: #0a0e17; color: #e0e6ed; }
h1, h2, h3, h4 { color: #00e5ff !important; }
.stMetric label { color: #607d8b !important; }
.stMetric [data-testid="stMetricValue"] { color: #00e5ff !important; }
.stTextInput>div>div>input, .stTextArea textarea {
    background: #151d2b !important; color: #e0e6ed !important;
    border: 1px solid #1e3a5f !important; border-radius: 6px;
}
.stSelectbox>div>div { background: #151d2b !important; color: #e0e6ed !important; }
.stButton>button {
    background: #1e3a5f !important; color: #00e5ff !important;
    border: 1px solid #00e5ff44 !important; border-radius: 6px;
}
.stButton>button:hover { background: #2a4a7f !important; }

/* Chat rows — group chat style */
.chat-row {
    margin: 6px 0;
    padding: 8px 12px;
    border-radius: 6px;
    background: #111927;
    border: 1px solid #1a2a44;
}
.chat-row.thinking {
    border-left: 3px solid #ffab00;
    animation: pulse 1.5s ease-in-out infinite;
}
.chat-row.system {
    border-left: 3px solid #607d8b;
    opacity: 0.7;
}
.chat-row.artifact {
    border-left: 3px solid #00c853;
}
.chat-row.approval {
    border-left: 3px solid #ff5252;
}
.chat-row.collaboration {
    border-left: 3px solid #00e5ff;
    background: #0d1a2d;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.6; }
}
.chat-header {
    display: flex; align-items: center; margin-bottom: 2px;
}
.chat-from-name { color: #00e5ff; font-weight: 600; font-size: 0.82em; margin: 0 4px; }
.chat-arrow { color: #607d8b; margin: 0 4px; font-size: 0.75em; }
.chat-to-name { color: #8fa4b8; font-size: 0.78em; margin: 0 4px; }
.chat-ts { color: #455a64; font-size: 0.65em; margin-left: auto; }
.chat-text {
    margin: 2px 0 0 4px; color: #ccd6dd; font-size: 0.88em;
}

/* Decision cards */
.decision-card {
    background: #111927; border: 1px solid #1e3a5f;
    padding: 10px 14px; margin: 4px 0; border-radius: 6px;
}
.decision-icon { font-size: 1.4em; }
.decision-title { color: #00e5ff; font-weight: 600; }
.decision-detail { color: #8fa4b8; font-size: 0.85em; }

/* Pipeline board */
.phase-dot { font-size: 0.6em; color: #607d8b; }
</style>
"""

AGENT_CONFIGS = [
    {"id": "product_manager", "name": "Product Manager", "emoji": "📋", "color": "#00e5ff"},
    {"id": "system_architect", "name": "System Architect", "emoji": "🏗️", "color": "#7c4dff"},
    {"id": "code_writer", "name": "Code Writer", "emoji": "💻", "color": "#00c853"},
    {"id": "test_engineer", "name": "Test Engineer", "emoji": "🧪", "color": "#ffab00"},
    {"id": "code_reviewer", "name": "Code Reviewer", "emoji": "🔍", "color": "#ff5252"},
    {"id": "devops", "name": "DevOps", "emoji": "🚀", "color": "#448aff"},
]


@st.cache_resource
def get_session() -> PipelineSession:
    return PipelineSession()


def main():
    st.set_page_config(page_title="CodeForge AI", page_icon="🔨", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("🔨 CodeForge AI")
    st.caption("Multi-Agent Software Development Command Center")

    session = get_session()
    state = session.get_state()

    _render_project_form(session)

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Live Comms", "Pipeline", "Decisions", "Artifacts", "Plan",
    ])

    with tab1:
        render_conversation(session, state)
    with tab2:
        render_control_room(session, state)
    with tab3:
        render_decisions(state)
    with tab4:
        render_artifacts(state)
    with tab5:
        render_plan_thread(state)


def render_conversation(session: PipelineSession, state: dict):
    st.header("Agent Conversation Feed")
    dialogue = state.get("dialogue", [])
    raw_messages = state.get("messages", [])

    col_a, col_b, col_c = st.columns([2, 1, 1])
    with col_b:
        kinds = ["All"] + (
            sorted({d.get("kind", "") for d in dialogue if d.get("kind")})
            if dialogue else []
        )
        kind_filter = st.selectbox("Filter", kinds, key="dialogue_filter")
    with col_c:
        show_raw = st.checkbox("Show raw protocol", key="show_raw_msgs",
                               value=not bool(dialogue))

    with col_a:
        st.caption(
            f"Dialogue: {len(dialogue)} entries | "
            f"Messages: {state.get('message_count', 0)}"
        )

    if not dialogue and not raw_messages:
        st.info("No messages yet. Start a project above to see agents talk.")
        return

    with st.container(height=520):
        if show_raw and raw_messages:
            st.caption("Raw protocol messages:")
            for msg in reversed(raw_messages[-40:]):
                mt = msg.get("type", "?")
                sn = msg.get("sender", "?")
                rc = msg.get("recipient", "?")
                pl = str(msg.get("payload", {}))[:100]
                st.markdown(
                    f'<div class="chat-row system">'
                    f'<div class="chat-header">'
                    f'<span class="chat-from-name">{sn}</span>'
                    f'<span class="chat-arrow">></span>'
                    f'<span class="chat-to-name">{rc}</span>'
                    f'<span class="chat-ts">[{mt}]</span>'
                    f'</div>'
                    f'<div class="chat-text">{pl}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
        elif dialogue:
            for entry in reversed(dialogue[-80:]):
                if kind_filter != "All" and entry.get("kind") != kind_filter:
                    continue
                kind = entry.get("kind", "status")
                has_style = kind in (
                    "thinking", "system", "artifact", "approval",
                    "collaboration",
                )
                row_class = f"chat-row {kind}" if has_style else "chat-row"
                text = entry.get("text", "")
                if kind == "thinking":
                    text = f'{text} <span class="thinking-dots"></span>'

                bubble_html = (
                    f'<div class="{row_class}">'
                    f'<div class="chat-header">'
                    f'<span class="chat-from-name">'
                    f'{entry["sender_avatar"]} {entry["sender_name"]}</span>'
                    f'<span class="chat-arrow">></span>'
                    f'<span class="chat-to-name">'
                    f'{entry["recipient_avatar"]} {entry["recipient_name"]}</span>'
                    f'<span class="chat-ts">'
                    f'{entry.get("timestamp", "")[:19]}</span>'
                    f'</div>'
                    f'<div class="chat-text">{text}</div>'
                )

                reasoning = entry.get("reasoning", "")
                plan = entry.get("plan_snippet", "")
                if reasoning or plan:
                    bubble_html += (
                        '<div style="margin-left:24px; margin-top:4px; '
                        'font-size:0.76em;">'
                    )
                    if reasoning:
                        bubble_html += (
                            f'<span style="color:#607d8b;">Reasoning: </span>'
                            f'<span style="color:#8fa4b8;">{reasoning}</span>'
                        )
                    if plan:
                        bubble_html += (
                            f'<br><span style="color:#ffab00; font-weight:600;">'
                            f'Plan: </span>'
                            f'<span style="color:#ccc;">{plan}</span>'
                        )
                    bubble_html += '</div>'

                bubble_html += '</div>'
                st.markdown(bubble_html, unsafe_allow_html=True)
        else:
            st.info("No dialogue entries synthesized. Check 'Show raw protocol' ")


def render_control_room(session: PipelineSession, state: dict):
    st.header("Pipeline Control Room")

    current_phase = state["phase"]
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("Project", state["project_id"][:8] if state["project_id"] else "—")
    with col2:
        st.metric("Phase", current_phase.upper() if current_phase != "complete" else "COMPLETE")
    with col3:
        artifacts = state.get("artifacts", {})
        st.metric("Artifacts", len(artifacts))
    with col4:
        st.metric("Messages", state["message_count"])
    with col5:
        decisions = state.get("decisions", [])
        st.metric("Decisions", len(decisions))

    st.subheader("Phase Map")
    current_idx = PHASES_LIST.index(current_phase) if current_phase in PHASES_LIST else -1
    phase_icons = {
        "requirements": "📋", "architecture": "🏗️", "implementation": "💻",
        "testing": "🧪", "review": "🔍", "deployment": "🚀", "complete": "🏁",
    }
    cols = st.columns(len(PHASES_LIST))
    for i, (col, p) in enumerate(zip(cols, PHASES_LIST)):
        with col:
            if i < current_idx:
                st.markdown(f"### {phase_icons[p]}")
                st.caption(f"✅ {p.capitalize()}")
            elif i == current_idx:
                st.markdown(f"### {phase_icons[p]}")
                st.caption(f"⚡ **{p.capitalize()}**")
            else:
                st.markdown("◻")
                st.caption(p.capitalize())

    st.subheader("Agent Status Board")

    phase_agents = {
        "requirements": "product_manager",
        "architecture": "system_architect",
        "implementation": "code_writer",
        "testing": "test_engineer",
        "review": "code_reviewer",
        "deployment": "devops",
    }
    current_agent_id = phase_agents.get(current_phase)

    agents_from_state = state.get("agents", [])
    for cfg in AGENT_CONFIGS:
        ag_state = "idle"
        progress = 0.0
        for a in agents_from_state:
            if a.get("role") == cfg["id"]:
                ag_state = a.get("state", "idle")
                progress = a.get("progress", 0.0)
                break

        is_current = cfg["id"] == current_agent_id

        cols = st.columns([1, 3, 2, 2, 2])
        with cols[0]:
            st.markdown(f"### {cfg['emoji']}")
        with cols[1]:
            marker = "▶ " if is_current else ""
            st.markdown(f"**{marker}{cfg['name']}**")
        with cols[2]:
            st.progress(progress)
        with cols[3]:
            state_color = {
                "idle": "gray", "working": "green", "blocked": "orange",
                "error": "red",
            }.get(ag_state, "gray")
            st.markdown(f":{state_color}[{ag_state}]")
        with cols[4]:
            st.caption(
                f"{cfg['color']}" if is_current else "#607d8b"
            )


def _render_project_form(session: PipelineSession):
    has_project = bool(session.get_state().get("project_id"))
    if has_project:
        with st.expander("Start New Project", expanded=False):
            _project_form_body(session)
    else:
        st.subheader("Start New Project")
        _project_form_body(session)


def _project_form_body(session: PipelineSession):
    col1, col2 = st.columns([3, 1])
    with col1:
        spec = st.text_area(
            "Specification",
            key="spec_input",
            placeholder="e.g. 'Build a todo app with user auth, CRUD, CSV export, and a dashboard'",
            height=90,
        )
    with col2:
        output = st.text_input("Output Dir", value=".codeforge/output", key="output_dir")
        if st.button("▶ Run Pipeline", type="primary", use_container_width=True):
            if spec.strip():
                with st.spinner("Agents are collaborating on your project..."):
                    result = session.run_sync(spec, output)
                    st.success(
                        f"Pipeline finished — Phase: {result['phase']} | "
                        f"Artifacts: {list(result['artifacts'].keys())}"
                    )
                    st.rerun()
            else:
                st.warning("Enter a specification first")


def render_decisions(state: dict):
    st.header("Decisions Board")
    decisions = state.get("decisions", [])

    if not decisions:
        st.info("No decisions yet. Start a project to see agent decision-making.")
        return

    st.caption(f"{len(decisions)} decisions logged across the pipeline")
    for d in decisions:
        st.markdown(
            f'<div class="decision-card">'
            f'<span class="decision-icon">{d["icon"]}</span> '
            f'<span class="decision-title">{d["title"]}</span><br>'
            f'<span class="decision-detail">{d["detail"]}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_artifacts(state: dict):
    st.header("Artifact Explorer")
    artifacts = state.get("artifacts", {})

    art_configs = [
        ("prd", "📋 PRD"),
        ("tech_spec", "🏗️ Tech Spec"),
        ("source_code", "💻 Source Code"),
        ("test_suite", "🧪 Test Suite"),
        ("review_report", "🔍 Review Report"),
        ("deployment_config", "🚀 Deployment"),
    ]

    status_cols = st.columns(len(art_configs))
    for col, (key, label) in zip(status_cols, art_configs):
        with col:
            present = key in artifacts
            color = "green" if present else "gray"
            st.markdown(f":{color}_circle: {label}")

    tabs = st.tabs([label for _, label in art_configs])

    with tabs[0]:
        _render_prd(artifacts.get("prd", {}))
    with tabs[1]:
        _render_techspec(artifacts.get("tech_spec", {}))
    with tabs[2]:
        _render_source(artifacts.get("source_code", {}))
    with tabs[3]:
        _render_test(artifacts.get("test_suite", {}))
    with tabs[4]:
        _render_review(artifacts.get("review_report", {}))
    with tabs[5]:
        _render_deploy(artifacts.get("deployment_config", {}))


def _render_prd(data: dict):
    if not data:
        st.info("Not yet generated")
        return
    st.subheader(data.get("title", "Untitled"))
    st.write(data.get("summary", ""))
    with st.expander("Goals"):
        st.json(data.get("goals", []))
    stories = data.get("user_stories", [])
    if stories:
        with st.expander(f"User Stories ({len(stories)})"):
            for i, s in enumerate(stories[:10]):
                st.caption(f"{i+1}. {s.get('statement', str(s))}")
    with st.expander("Scope & Edge Cases"):
        st.json(data.get("scope", {}))
        st.json(data.get("edge_cases", []))


def _render_techspec(data: dict):
    if not data:
        st.info("Not yet generated")
        return
    st.subheader(data.get("title", ""))
    st.write(data.get("overview", ""))
    with st.expander("Tech Stack"):
        for item in data.get("tech_stack", []):
            st.markdown(
                f"- **{item.get('category', '')}**: {item.get('choice', '')} "
                f"({item.get('rationale', '')})"
            )
    with st.expander("Data Entities"):
        st.json(data.get("data_entities", []))
    with st.expander("API Endpoints"):
        for ep in data.get("api_endpoints", []):
            st.markdown(
                f"- {ep.get('method', 'GET')} {ep.get('path', '/')}"
                f" — {ep.get('summary', '')}"
            )
    with st.expander("File Tree"):
        st.json(data.get("file_tree", []))
    with st.expander("Risks"):
        for r in data.get("risks", []):
            st.markdown(
                f"- **{r.get('description', '')}**"
                f" (severity: {r.get('severity', '')})"
            )


def _render_source(data: dict):
    if not data:
        st.info("Not yet generated")
        return
    st.metric("Files", len(data.get("files", [])))
    st.caption(data.get("validation_report", ""))
    with st.expander("Files Created"):
        for f in data.get("files", []):
            st.text(f)
    editor = data.get("editor_summary", {})
    if editor:
        with st.expander("Editor Summary"):
            st.json(editor)


def _render_test(data: dict):
    if not data:
        st.info("Not yet generated")
        return
    st.metric("Test Files", len(data.get("test_files", [])))
    st.metric("Patterns", data.get("patterns_generated", 0))
    st.caption(data.get("coverage_report", ""))
    with st.expander("Test Files"):
        for f in data.get("test_files", []):
            st.text(f)
    missing = data.get("missing_tests", [])
    if missing:
        with st.expander("Coverage Gaps"):
            for m in missing:
                st.warning(m)


def _render_review(data: dict):
    if not data:
        st.info("Not yet generated")
        return
    score = data.get("overall_score", 0)
    st.metric("Score", f"{score:.1%}" if isinstance(score, float) else str(score))
    st.metric("Findings", data.get("total_findings", 0))
    st.metric("Layers Analyzed", data.get("layers_analyzed", 0))
    with st.expander("Findings"):
        st.json(data.get("findings", []))


def _render_deploy(data: dict):
    if not data:
        st.info("Not yet generated")
        return
    st.metric("Files", len(data.get("files_generated", [])))
    for f in data.get("files_generated", []):
        st.text(f)


def render_plan_thread(state: dict):
    st.header("Plan Thread")
    dialogue = state.get("dialogue", [])

    collab_entries = [
        d for d in dialogue
        if d.get("kind") in ("collaboration", "task") and d.get("plan_snippet")
    ]

    if not collab_entries:
        st.info("No plan entries yet. Start a project to see agent strategy discussions.")
        return

    for entry in reversed(collab_entries):
        reason = entry.get("reasoning", "")
        plan = entry.get("plan_snippet", "")
        text = entry.get("text", "")

        with st.container():
            st.markdown(
                f'<div class="decision-card">'
                f'<span class="decision-icon">'
                f'{entry["sender_avatar"]}</span> '
                f'<span class="decision-title">'
                f'{entry["sender_name"]}'
                f'</span>'
                f'</div>',
                unsafe_allow_html=True,
            )
            if reason:
                st.caption(f"Reasoning: {reason}")
            if plan:
                st.markdown(f"**Plan:** {plan}")
            st.caption(f"Message: {text[:120]}")


if __name__ == "__main__":
    main()
