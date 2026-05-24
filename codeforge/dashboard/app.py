"""Streamlit Dashboard for CodeForge — Messenger-style command center.

Clean group chat with bubbles, agent avatars, reasoning, and plan threads.
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
/* Dark messenger theme */
.main, .stApp { background: #0d1117; color: #c9d1d9; }
h1, h2, h3 { color: #58a6ff !important; }
.stMetric label { color: #8b949e !important; font-size: 0.7em !important; }
.stMetric [data-testid="stMetricValue"] { color: #58a6ff !important; }
input, textarea, .stSelectbox>div>div {
    background: #161b22 !important; color: #c9d1d9 !important;
    border: 1px solid #30363d !important; border-radius: 8px;
}
.stButton>button {
    background: #238636 !important; color: #fff !important;
    border: 1px solid #2ea043 !important; border-radius: 8px; font-weight: 600;
}
.stButton>button:hover { background: #2ea043 !important; }

/* Chat container */
.chat-container {
    max-height: 62vh; overflow-y: auto; padding: 8px 4px;
    background: #0d1117; border: 1px solid #21262d; border-radius: 10px;
}
.msg-group { margin-bottom: 14px; }
.msg-row { display: flex; align-items: flex-start; margin: 2px 0; }
.msg-avatar { font-size: 20px; width: 34px; text-align: center; flex-shrink: 0; padding-top: 2px; }
.msg-body { margin-left: 8px; max-width: 85%; }
.msg-sender {
    font-weight: 700; font-size: 0.82em; margin-bottom: 1px;
}
.msg-to { color: #8b949e; font-weight: 400; }
.msg-bubble {
    background: #161b22; padding: 7px 12px; border-radius: 12px;
    border-top-left-radius: 3px; line-height: 1.45; font-size: 0.88em;
    color: #c9d1d9; word-break: break-word;
}
.msg-bubble.collab { border-left: 3px solid #58a6ff;  background: #0d1a2d; }
.msg-bubble.artifact { border-left: 3px solid #3fb950; }
.msg-bubble.thinking { border-left: 3px solid #d29922; animation: flash 1.2s ease-in-out infinite; }
.msg-bubble.system { border-left: 3px solid #8b949e; opacity: 0.6; font-size: 0.76em; }
.msg-bubble.approval { border-left: 3px solid #f85149; }
@keyframes flash { 0%,100% { opacity: 1; } 50% { opacity: 0.55; } }
.msg-reason {
    margin-top: 4px; font-size: 0.74em; color: #8b949e;
    border-top: 1px solid #21262d; padding-top: 4px;
}
.msg-plan {
    margin-top: 2px; font-size: 0.74em; color: #d29922;
    font-weight: 600;
}
.msg-ts { font-size: 0.64em; color: #484f58; margin-left: 6px; }

.thinking-dots::after { content: ''; animation: dots 2s steps(4) infinite; }
@keyframes dots { 0% { content: ''; } 25% { content: ' .'; }
  50% { content: ' ..'; } 75% { content: ' ...'; } }

/* Plan cards */
.plan-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 10px 14px; margin: 6px 0;
}
.plan-from { color: #58a6ff; font-weight: 600; font-size: 0.85em; }
.plan-reason { color: #8b949e; font-size: 0.78em; margin-top: 2px; }
.plan-snippet { color: #d29922; font-size: 0.8em; font-weight: 600; margin-top: 4px; }

/* Decisions */
.dec-card {
    background: #161b22; border: 1px solid #30363d; border-radius: 8px;
    padding: 10px 14px; margin: 4px 0;
}
.dec-icon { font-size: 1.3em; margin-right: 6px; }
.dec-title { color: #58a6ff; font-weight: 600; }
.dec-detail { color: #8b949e; font-size: 0.82em; }
</style>
"""

AGENT_CFG = [
    ("product_manager", "Product Manager", "\U0001f4cb", "#58a6ff"),
    ("system_architect", "System Architect", "\U0001f3d7\ufe0f", "#bc8cff"),
    ("code_writer", "Code Writer", "\U0001f4bb", "#3fb950"),
    ("test_engineer", "Test Engineer", "\U0001f9ea", "#d29922"),
    ("code_reviewer", "Code Reviewer", "\U0001f50d", "#f85149"),
    ("devops", "DevOps", "\U0001f680", "#79c0ff"),
]


@st.cache_resource
def get_session() -> PipelineSession:
    return PipelineSession()


def main():
    st.set_page_config(page_title="CodeForge AI", page_icon="\U0001f528", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("\U0001f528 CodeForge AI")
    st.caption("Multi-Agent Development — Messenger Command Center")

    session = get_session()
    state = session.get_state()

    _render_project_bar(session, state)

    tab1, tab2, tab3 = st.tabs(["Chat", "Pipeline", "Decisions"])

    with tab1:
        render_chat(state)
    with tab2:
        render_pipeline(state)
    with tab3:
        render_decisions(state)


def _render_project_bar(session, state):
    pid = state["project_id"]
    phase = state["phase"]
    artifacts = state.get("artifacts", {})

    cols = st.columns([1, 1, 1, 1, 3])
    with cols[0]:
        st.metric("Project", pid[:8] if pid else "\u2014")
    with cols[1]:
        st.metric("Phase", phase.upper()[:12])
    with cols[2]:
        st.metric("Artifacts", len(artifacts))
    with cols[3]:
        st.metric("Messages", state["message_count"])

    with cols[4]:
        with st.expander("New Project", expanded=not pid):
            c1, c2 = st.columns([3, 1])
            with c1:
                spec = st.text_area(
                    "Spec", key="spec_input", height=70,
                    placeholder="e.g. Build a SaaS task manager with auth, CRUD, CSV export...",
                )
            with c2:
                out = st.text_input("Output", value=".codeforge/output", key="out_dir")
                if st.button("Run", type="primary", use_container_width=True):
                    if spec.strip():
                        with st.spinner("Agents collaborating..."):
                            result = session.run_sync(spec, out)
                            st.success(f"Done: {result['phase']}")
                            st.rerun()
                    else:
                        st.warning("Enter a spec")


def render_chat(state):
    st.subheader("Group Chat")
    dialogue = state.get("dialogue", [])
    raw = state.get("messages", [])

    has_msgs = bool(dialogue or raw)
    show_raw = not dialogue and raw

    if not has_msgs:
        st.info("No messages yet. Start a project above.")
        return

    if show_raw:
        with st.container(height=500):
            for msg in reversed(raw[-40:]):
                st.caption(
                    f"[{msg.get('type','?')}] "
                    f"{msg.get('sender','?')} \u2192 {msg.get('recipient','?')}: "
                    f"{str(msg.get('payload',{}))[:100]}"
                )
        return

    colors = [
        "#58a6ff", "#bc8cff", "#3fb950", "#d29922", "#f85149", "#79c0ff",
    ]
    agent_color = {}
    for i, (aid, _, emoji, _) in enumerate(AGENT_CFG):
        agent_color[aid] = (emoji, colors[i % len(colors)])

    groups = _group_messages(dialogue)

    with st.container(height=540):
        for group in groups:
            entries = group["entries"]
            last_ts = entries[-1].get("timestamp", "")[:19]
            sender = entries[0].get("sender", "")
            s_name = entries[0].get("sender_name", "Agent")
            s_av = entries[0].get("sender_avatar", "\U0001f916")
            r_name = entries[0].get("recipient_name", "")

            color = agent_color.get(sender, ("", "#8b949e"))[1]
            st.markdown(
                f'<div class="msg-group">'
                f'<div class="msg-row">'
                f'<div class="msg-avatar">{s_av}</div>'
                f'<div class="msg-body">'
                f'<div class="msg-sender" style="color:{color}">'
                f'{s_name}'
                f'<span class="msg-to"> @ {r_name}</span>'
                f'<span class="msg-ts">{last_ts}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

            for entry in entries:
                kind = entry.get("kind", "status")
                text = entry.get("text", "")
                if kind == "thinking":
                    text = f'{text}<span class="thinking-dots"></span>'
                bclass = f"msg-bubble {kind}" if kind in (
                    "collab", "artifact", "thinking", "system", "approval"
                ) else "msg-bubble"

                html = f'<div class="{bclass}">{text}</div>'
                reason = entry.get("reasoning", "")
                plan = entry.get("plan_snippet", "")
                if reason:
                    html += f'<div class="msg-reason">Reason: {reason}</div>'
                if plan:
                    html += f'<div class="msg-plan">Plan: {plan}</div>'
                st.markdown(html, unsafe_allow_html=True)

            st.markdown('</div></div>', unsafe_allow_html=True)


def _group_messages(dialogue):
    groups = []
    current = None
    for entry in dialogue:
        sender = entry.get("sender", "")
        if current and current["sender"] == sender:
            current["entries"].append(entry)
        else:
            current = {"sender": sender, "entries": [entry]}
            groups.append(current)
    return groups


def render_pipeline(state):
    st.subheader("Pipeline Control Room")

    phase = state["phase"]
    current_idx = PHASES_LIST.index(phase) if phase in PHASES_LIST else -1
    phase_icons = {
        "requirements": "\U0001f4cb", "architecture": "\U0001f3d7\ufe0f",
        "implementation": "\U0001f4bb", "testing": "\U0001f9ea",
        "review": "\U0001f50d", "deployment": "\U0001f680", "complete": "\U0001f3c1",
    }

    cols = st.columns(len(PHASES_LIST))
    for i, (col, p) in enumerate(zip(cols, PHASES_LIST)):
        with col:
            if i < current_idx:
                st.markdown(f"### {phase_icons.get(p,'')}")
                st.caption(f"\u2705 {p.capitalize()}")
            elif i == current_idx:
                st.markdown(f"### {phase_icons.get(p,'')}")
                st.caption(f"\u26a1 {p.capitalize()}")
            else:
                st.markdown("### \u25ef")
                st.caption(p.capitalize())

    phase_agent_map = {
        "requirements": "product_manager",
        "architecture": "system_architect",
        "implementation": "code_writer",
        "testing": "test_engineer",
        "review": "code_reviewer",
        "deployment": "devops",
    }
    current_agent = phase_agent_map.get(phase)

    agents_from_state = state.get("agents", [])
    st.subheader("Agents")

    for aid, name, emoji, color in AGENT_CFG:
        ag = {"state": "idle", "progress": 0.0}
        for a in agents_from_state:
            if a.get("role") == aid:
                ag = a
                break

        is_current = aid == current_agent
        sts = ag.get("state", "idle")
        prg = ag.get("progress", 0.0)

        c1, c2, c3, c4 = st.columns([1, 3, 2, 1])
        with c1:
            st.markdown(f"### {emoji}")
        with c2:
            marker = "\u25b6 " if is_current else "  "
            st.markdown(f"**{marker}{name}**")
        with c3:
            st.progress(prg)
        with c4:
            dot = {"idle": "gray", "working": "green", "blocked": "orange",
                   "error": "red"}.get(sts, "gray")
            st.markdown(f":{dot}[{sts}]")

    if state.get("errors"):
        st.error(" | ".join(state["errors"]))


def render_decisions(state):
    st.subheader("Decisions & Plans")

    dialogue = state.get("dialogue", [])
    collab = [
        d for d in dialogue
        if d.get("kind") in ("collaboration", "task")
        and d.get("plan_snippet")
    ]

    decisions = state.get("decisions", [])

    if not collab and not decisions:
        st.info("No decisions yet. Start a project.")
        return

    if collab:
        for entry in reversed(collab[-12:]):
            st.markdown(
                f'<div class="plan-card">'
                f'<div class="plan-from">'
                f'{entry["sender_avatar"]} {entry["sender_name"]}'
                f'</div>'
                f'<div class="plan-reason">'
                f'{entry.get("reasoning", "")}</div>'
                f'<div class="plan-snippet">'
                f'\U0001f4cb {entry.get("plan_snippet", "")}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    if decisions:
        st.subheader("Artifact Decisions")
        for d in decisions:
            st.markdown(
                f'<div class="dec-card">'
                f'<span class="dec-icon">{d["icon"]}</span>'
                f'<span class="dec-title">{d["title"]}</span><br>'
                f'<span class="dec-detail">{d["detail"]}</span>'
                f'</div>',
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
