"""Quick demo runner for CodeForge."""
import asyncio
import os
import tempfile

from codeforge.api.session import PipelineSession


async def demo():
    with tempfile.TemporaryDirectory() as tmp:
        session = PipelineSession(storage_path=os.path.join(tmp, ".cf"))
        pid = await session.start(
            "Build a task management app with CRUD, search, and CSV export",
            os.path.join(tmp, "out"),
        )
        state = session.get_state()
        print(f"Project ID: {pid[:8]}")
        print(f"Phase: {state['phase']}")
        print(f"Agents registered: {len(state.get('agents', []))}")
        print(f"Messages generated: {state['message_count']}")
        print(f"Artifacts produced: {list(state.get('artifacts', {}).keys())}")
        print("Pipeline running successfully!")


asyncio.run(demo())
