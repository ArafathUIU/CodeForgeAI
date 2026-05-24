"""Streamlit Dashboard for CodeForge — Production Command Center."""

from __future__ import annotations

import streamlit as st

from codeforge.api.session import PipelineSession

PHASES = [
    "requirements", "architecture", "implementation",
    "testing", "review", "deployment", "complete",
]

CSS = """
<style>
/* === Production theme — clean SaaS palette === */
.main, .stApp { background: #f4f6f9; color: #1e293b; }
h1, h2, h3, h4 { color: #0f172a !important; font-weight: 700; }
.stMetric label { color: #64748b !important; font-size: 0.68em !important;
  text-transform: uppercase; letter-spacing: 0.05em; }
.stMetric [data-testid="stMetricValue"] { color: #0f172a !important;
  font-weight: 700; }
input, textarea, .stSelectbox>div>div {
    background: #fff !important; color: #1e293b !important;
    border: 1px solid #e2e8f0 !important; border-radius: 8px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.stButton>button {
    background: #3b82f6 !important; color: #fff !important;
    border: none !important; border-radius: 8px; font-weight: 600;
    padding: 8px 16px; cursor: pointer;
    box-shadow: 0 1px 3px rgba(59,130,246,0.3);
}
.stButton>button:hover { background: #2563eb !important; }

/* Sidebar */
[data-testid="stSidebar"] { background: #0f172a; }
[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
[data-testid="stSidebar"] .stTextInput input,
[data-testid="stSidebar"] .stTextArea textarea {
    background: #1e293b !important; color: #e2e8f0 !important;
    border: 1px solid #334155 !important;
}
[data-testid="stSidebar"] .stButton>button {
    background: #3b82f6 !important;
}

/* === Chat === */
.chat-scroll {
    max-height: 58vh; overflow-y: auto; padding-right: 6px;
    background: #fff; border-radius: 12px;
    padding: 16px; border: 1px solid #e2e8f0;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.msg-group { margin-bottom: 18px; }
.msg-header {
    display: flex; align-items: center; margin-bottom: 4px;
}
.msg-avatar { font-size: 22px; width: 30px; text-align: center; }
.msg-sender {
    font-weight: 700; font-size: 0.82em; margin-left: 6px;
}
.msg-to { color: #94a3b8; font-weight: 400; margin-left: 2px; font-size: 0.9em; }
.msg-ts { color: #94a3b8; font-size: 0.66em; margin-left: auto; }
.msg-bubble {
    background: #fff; padding: 8px 14px; border-radius: 14px;
    border: 1px solid #e2e8f0; font-size: 0.88em;
    color: #1e293b; line-height: 1.5; margin-left: 36px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
.msg-bubble.collab {
    border-left: 3px solid #3b82f6; background: #f8fafc;
}
.msg-bubble.artifact {
    border-left: 3px solid #10b981;
}
.msg-bubble.thinking {
    border-left: 3px solid #f59e0b;
    animation: pulse-slow 2s ease-in-out infinite;
}
.msg-bubble.system {
    border-left: 3px solid #94a3b8; opacity: 0.65; font-size: 0.78em;
}
.msg-bubble.approval {
    border-left: 3px solid #ef4444;
}
@keyframes pulse-slow {
    0%, 100% { opacity: 1; } 50% { opacity: 0.55; }
}
.msg-reason {
    margin-top: 4px; font-size: 0.72em; color: #64748b;
    border-top: 1px solid #f1f5f9; padding-top: 4px;
}
.msg-plan {
    margin-top: 2px; font-size: 0.72em; color: #f59e0b; font-weight: 600;
}

/* Thinking dots */
.think-dots::after {
    content: ''; animation: ellipsis 2s steps(4) infinite;
}
@keyframes ellipsis {
    0% { content: ''; } 25% { content: '.'; }
    50% { content: '..'; } 75% { content: '...'; }
}

/* Cards */
.card {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 10px;
    padding: 14px 18px; margin: 6px 0;
    box-shadow: 0 1px 3px rgba(0,0,0,0.04);
}
.card-title { color: #0f172a; font-weight: 700; font-size: 0.88em; }
.card-sub { color: #64748b; font-size: 0.78em; margin-top: 2px; }

/* Phase dots */
.phase-item {
    text-align: center; padding: 4px 0;
}
.phase-icon { font-size: 1.4em; }
.phase-label { font-size: 0.62em; color: #94a3b8; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.04em; }
.phase-label.active { color: #3b82f6; }
.phase-label.done { color: #10b981; }

/* Agent row */
.agent-row {
    display: flex; align-items: center; padding: 5px 0;
}
.agent-dot {
    width: 8px; height: 8px; border-radius: 50%; display: inline-block;
    margin-right: 8px;
}
.agent-name { font-size: 0.82em; font-weight: 600; }
</style>
"""

AGENTS = [
    ("product_manager", "Product Manager", "\U0001f4cb", "#3b82f6"),
    ("system_architect", "System Architect", "\U0001f3d7\ufe0f", "#8b5cf6"),
    ("code_writer", "Code Writer", "\U0001f4bb", "#10b981"),
    ("test_engineer", "Test Engineer", "\U0001f9ea", "#f59e0b"),
    ("code_reviewer", "Code Reviewer", "\U0001f50d", "#ef4444"),
    ("devops", "DevOps", "\U0001f680", "#06b6d4"),
]


@st.cache_resource
def get_session() -> PipelineSession:
    return PipelineSession()


def main():
    st.set_page_config(
        page_title="CodeForge AI",
        page_icon="\U0001f528",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CSS, unsafe_allow_html=True)

    session = get_session()
    state = session.get_state()

    _render_sidebar(session, state)

    col_main, col_right = st.columns([3, 1])

    with col_main:
        st.title("\U0001f528 CodeForge AI")
        st.caption("Multi-Agent Software Development Command Center")
        render_chat(state)

    with col_right:
        render_pipeline_panel(state)
        render_agent_panel(state)
        render_decisions_panel(state)


def _render_sidebar(session, state):
    with st.sidebar:
        st.title("\U0001f528 CodeForge")

        pid = state["project_id"]
        if pid:
            st.metric("Project", pid[:8])
            st.metric("Phase", state["phase"].upper())
            st.metric("Artifacts", len(state.get("artifacts", {})))
            st.metric("Messages", state["message_count"])
        else:
            st.caption("No active project")

        st.divider()
        st.subheader("New Project")

        spec = st.text_area(
            "Specification", key="spec_input", height=90,
            placeholder="e.g. Build a SaaS task manager with auth...",
        )
        out = st.text_input("Output Directory", value=".codeforge/output", key="out_dir")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Run Pipeline", type="primary", use_container_width=True):
                if spec.strip():
                    with st.spinner("Agents collaborating..."):
                        result = session.run_sync(spec, out)
                        st.success(f"Done: {result['phase']}")
                        st.rerun()
                else:
                    st.warning("Enter a specification")
        with c2:
            if st.button("Reset", use_container_width=True):
                st.cache_resource.clear()
                st.rerun()


def render_chat(state):
    dialogue = state.get("dialogue", [])
    raw = state.get("messages", [])
    show_raw = not dialogue and raw

    if not dialogue and not raw:
        st.info("No messages yet. Start a project from the sidebar.")
        return

    if show_raw:
        with st.container(height=480):
            for msg in reversed(raw[-40:]):
                st.caption(
                    f"[{msg.get('type','?')}] "
                    f"{msg.get('sender','?')} > {msg.get('recipient','?')}: "
                    f"{str(msg.get('payload',{}))[:120]}"
                )
        return

    agent_colors = {}
    for i, (aid, _, _, clr) in enumerate(AGENTS):
        agent_colors[aid] = clr

    groups = _group(dialogue)

    st.markdown('<div class="chat-scroll">', unsafe_allow_html=True)
    for group in groups:
        entries = group["entries"]
        last_ts = entries[-1].get("timestamp", "")[:19]
        sender = entries[0].get("sender", "")
        s_name = entries[0].get("sender_name", "Agent")
        s_av = entries[0].get("sender_avatar", "\U0001f916")
        r_name = entries[0].get("recipient_name", "")
        color = agent_colors.get(sender, "#64748b")

        st.markdown(
            f'<div class="msg-group">'
            f'<div class="msg-header">'
            f'<span class="msg-avatar">{s_av}</span>'
            f'<span class="msg-sender" style="color:{color}">{s_name}</span>'
            f'<span class="msg-to">@ {r_name}</span>'
            f'<span class="msg-ts">{last_ts}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

        for entry in entries:
            kind = entry.get("kind", "status")
            text = entry.get("text", "")
            if kind == "thinking":
                text = f'{text}<span class="think-dots"></span>'
            bclass = f"msg-bubble {kind}" if kind in (
                "collab", "artifact", "thinking", "system", "approval"
            ) else "msg-bubble"

            html = f'<div class="{bclass}">{text}</div>'
            reason = entry.get("reasoning", "")
            plan = entry.get("plan_snippet", "")
            if reason:
                html += f'<div class="msg-reason">{reason}</div>'
            if plan:
                html += f'<div class="msg-plan">Plan: {plan}</div>'
            st.markdown(html, unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def _group(dialogue):
    groups = []
    cur = None
    for entry in dialogue:
        s = entry.get("sender", "")
        if cur and cur["sender"] == s:
            cur["entries"].append(entry)
        else:
            cur = {"sender": s, "entries": [entry]}
            groups.append(cur)
    return groups


def render_pipeline_panel(state):
    st.subheader("Pipeline")
    phase = state["phase"]
    current_idx = PHASES.index(phase) if phase in PHASES else -1
    icons = {
        "requirements": "\U0001f4cb", "architecture": "\U0001f3d7\ufe0f",
        "implementation": "\U0001f4bb", "testing": "\U0001f9ea",
        "review": "\U0001f50d", "deployment": "\U0001f680", "complete": "\U0001f3c1",
    }

    cols = st.columns(len(PHASES))
    for i, (col, p) in enumerate(zip(cols, PHASES)):
        with col:
            st.markdown('<div class="phase-item">', unsafe_allow_html=True)
            if i < current_idx:
                st.markdown(f'{icons[p]}', help=p)
                st.markdown('<div class="phase-label done">done</div>', unsafe_allow_html=True)
            elif i == current_idx:
                st.markdown(f'{icons[p]}', help=p)
                st.markdown(
                    f'<div class="phase-label active">{p[:4]}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(f'{icons[p]}', help=p)
                st.markdown(f'<div class="phase-label">{p[:4]}</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)


def render_agent_panel(state):
    st.subheader("Agents")
    phase_agent = {
        "requirements": "product_manager",
        "architecture": "system_architect",
        "implementation": "code_writer",
        "testing": "test_engineer",
        "review": "code_reviewer",
        "deployment": "devops",
    }
    agents_state = state.get("agents", [])

    for aid, name, emoji, color in AGENTS:
        ag = {"state": "idle", "progress": 0.0}
        for a in agents_state:
            if a.get("role") == aid:
                ag = a
                break

        sts = ag.get("state", "idle")
        dot_color = {"idle": "#94a3b8", "working": "#10b981",
                     "blocked": "#f59e0b", "error": "#ef4444"}.get(sts, "#94a3b8")
        is_current = aid == phase_agent.get(state["phase"])

        marker = "\u25b6 " if is_current else "  "

        st.markdown(
            f'<div class="agent-row">'
            f'<span class="agent-dot" style="background:{dot_color}"></span>'
            f'<span class="agent-name" style="color:{color}">'
            f'{marker}{emoji} {name}</span>'
            f'</div>',
            unsafe_allow_html=True,
        )


def render_decisions_panel(state):
    st.subheader("Decisions")
    decisions = state.get("decisions", [])
    if not decisions:
        st.caption("No decisions yet")
        return
    for d in decisions[-6:]:
        st.markdown(
            f'<div class="card">'
            f'<div class="card-title">{d["icon"]} {d["title"]}</div>'
            f'<div class="card-sub">{d["detail"]}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
