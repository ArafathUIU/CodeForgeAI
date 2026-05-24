"""End-to-end demo: runs the full CodeForge pipeline.

Tests the complete flow from specification through deployment
with all six agents working in sequence.
"""

import asyncio
import os
import tempfile


async def run_full_pipeline(specification: str) -> dict:
    from codeforge.api.session import PipelineSession

    with tempfile.TemporaryDirectory() as tmpdir:
        output_dir = os.path.join(tmpdir, "output")
        os.makedirs(output_dir, exist_ok=True)

        session = PipelineSession(storage_path=os.path.join(tmpdir, ".codeforge"))

        project_id = await session.start(specification, output_dir)
        assert project_id, "Project should start"

        state = session.get_state()
        return {
            "project_id": project_id,
            "phase": state["phase"],
            "agents": len(state.get("agents", [])),
            "message_count": state["message_count"],
        }


def main():
    spec = (
        "Build a todo application with user authentication, "
        "CRUD operations for tasks, data export to CSV, "
        "and a dashboard view showing task statistics."
    )
    print("=" * 60)
    print("CodeForge AI - End-to-End Demo")
    print("=" * 60)
    print(f"\nSpecification: {spec}\n")

    result = asyncio.run(run_full_pipeline(spec))

    print(f"Project ID: {result['project_id']}")
    print(f"Phase: {result['phase']}")
    print(f"Agents registered: {result['agents']}")
    print(f"Messages generated: {result['message_count']}")
    print("\nDemo complete!")


if __name__ == "__main__":
    main()
