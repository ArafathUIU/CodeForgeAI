"""Pipeline status view: shows current phase and progress."""

import streamlit as st


def render_pipeline_status():
    st.header("Pipeline Status")

    col1, col2, col3 = st.columns(3)

    with col1:
        _ = st.selectbox(
            "Current Phase",
            ["init", "requirements", "architecture", "implementation",
             "testing", "review", "deployment", "complete"],
            disabled=True,
        )

    with col2:
        st.metric("Progress", "0%")

    with col3:
        st.metric("Checkpoints", "0")

    phases = [
        "Requirements",
        "Architecture",
        "Implementation",
        "Testing",
        "Review",
        "Deployment",
    ]

    st.subheader("Phase Timeline")
    cols = st.columns(len(phases))
    for i, (col, p) in enumerate(zip(cols, phases)):
        with col:
            st.button(p[:4], key=f"phase_{i}", disabled=True, use_container_width=True)

    st.subheader("Project Actions")

    col1, col2 = st.columns(2)
    with col1:
        spec = st.text_area(
            "Project Specification",
            placeholder="Describe your app in natural language...",
            height=100,
        )
    with col2:
        _ = st.text_input("Output Directory", value="./codeforge_output")
        if st.button("Start Project", type="primary", use_container_width=True):
            st.info(f"Starting project with specification of {len(spec)} chars")
