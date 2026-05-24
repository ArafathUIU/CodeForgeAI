"""CodeForge CLI entry point."""

from __future__ import annotations

import argparse
import asyncio

from codeforge.api.session import PipelineSession


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CodeForge AI — Multi-Agent Software Development",
    )
    sub = parser.add_subparsers(dest="command")

    run_parser = sub.add_parser("start", help="Start a new project")
    run_parser.add_argument("spec", nargs="*", help="Project specification")
    run_parser.add_argument(
        "--spec-file", type=str, default=None,
        help="Read specification from a file",
    )
    run_parser.add_argument(
        "--output", "-o", type=str, default=".codeforge/output",
        help="Output directory",
    )

    sub.add_parser("demo", help="Run the quick demo")
    sub.add_parser("dashboard", help="Launch the Streamlit dashboard")

    args = parser.parse_args()

    if args.command == "dashboard":
        from codeforge.dashboard.app import main as dash_main
        dash_main()
    elif args.command == "demo":
        from demos.run_demo import demo
        asyncio.run(demo())
    elif args.command == "start":
        spec = " ".join(args.spec) if args.spec else ""
        if args.spec_file:
            with open(args.spec_file, encoding="utf-8") as f:
                spec = f.read().strip()
        if not spec:
            spec = input("Enter project specification: ").strip()
        if not spec:
            print("No specification provided.")
            raise SystemExit(1)

        async def _run():
            session = PipelineSession()
            pid = await session.start(spec, args.output)
            state = session.get_state()
            print(f"Project: {pid[:8]}")
            print(f"Phase: {state['phase']}")
            print(f"Artifacts: {list(state['artifacts'].keys())}")
            if state["phase"] == "complete":
                print("Pipeline completed successfully.")
            elif state["phase"] == "failed":
                print("Pipeline failed:", state.get("errors", []))

        asyncio.run(_run())
    else:
        parser.print_help()
