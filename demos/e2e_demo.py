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
            "artifacts": list(state.get("artifacts", {}).keys()),
            "approvals": len(state.get("approval_gates", [])),
        }


def main():
    spec = (
        "Build a todo application with user authentication, "
        "CRUD operations for tasks, data export to CSV, "
        "and a dashboard view showing task statistics."
    )
    print("=" * 60)
    print("  CodeForge AI — End-to-End Pipeline Demo")
    print("=" * 60)
    print(f"\n  Spec: {spec}\n")

    result = asyncio.run(run_full_pipeline(spec))

    print(f"  Project ID:      {result['project_id'][:8]}")
    print(f"  Final Phase:     {result['phase']}")
    print(f"  Agents:          {result['agents']}")
    print(f"  Messages:        {result['message_count']}")
    print(f"  Approvals:       {result['approvals']}")
    print("  Artifacts:")
    for a in result["artifacts"]:
        print(f"    - {a}")
    print(f"\n  Status: {'PASS' if result['phase'] == 'complete' else 'PARTIAL'}")

    return result["phase"] == "complete"


if __name__ == "__main__":
    ok = main()
    raise SystemExit(0 if ok else 1)
