"""Approval gate view: human-in-the-loop approval interface."""

import streamlit as st


def render_approval_gate():
    st.header("Approval Gates")

    st.info("Review and approve artifacts at critical pipeline phases.")

    gates = [
        {"phase": "Requirements", "artifact": "PRD", "status": "pending",
         "description": "Product Requirements Document for review"},
        {"phase": "Architecture", "artifact": "Tech Spec", "status": "pending",
         "description": "Technical specification for review"},
        {"phase": "Deployment", "artifact": "Deploy Config", "status": "pending",
         "description": "Deployment configuration for review"},
    ]

    for gate in gates:
        with st.expander(f"{gate['phase']}: {gate['artifact']} ({gate['status']})"):
            st.text(gate["description"])

            col1, col2 = st.columns(2)
            with col1:
                if st.button(f"Approve {gate['artifact']}", key=f"approve_{gate['artifact']}"):
                    st.success(f"Approved {gate['artifact']}!")
            with col2:
                comments = st.text_area(
                    "Revision notes",
                    key=f"comments_{gate['artifact']}",
                    placeholder="What needs to change?",
                )
                if st.button(f"Request Changes", key=f"reject_{gate['artifact']}"):
                    st.warning(f"Changes requested for {gate['artifact']}")
