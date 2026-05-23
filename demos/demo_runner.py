"""[7.11] Demo: Add demo runner CLI for running end-to-end scenarios."""

import argparse
import sys


def run_demo(demo_name: str) -> int:
    if demo_name == "todo":
        from demos.todo_app_demo import TODO_APP_SPEC

        print(f"Running demo: {TODO_APP_SPEC['name']}")
        print(f"Spec: {TODO_APP_SPEC['specification'][:80]}...")
        return 0

    if demo_name == "expense":
        from demos.expense_tracker_demo import EXPENSE_TRACKER_SPEC

        print(f"Running demo: {EXPENSE_TRACKER_SPEC['name']}")
        print(f"Spec: {EXPENSE_TRACKER_SPEC['specification'][:80]}...")
        return 0

    print(f"Unknown demo: {demo_name}")
    print("Available demos: todo, expense")
    return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        description="CodeForge Demo Runner"
    )
    parser.add_argument(
        "demo",
        nargs="?",
        choices=["todo", "expense", "list"],
        default="list",
        help="Demo scenario to run",
    )
    parser.add_argument(
        "--output-dir",
        default="./codeforge_demo_output",
        help="Output directory for generated code",
    )
    args = parser.parse_args()

    if args.demo == "list":
        print("Available demos:")
        print("  todo     - Todo Application")
        print("  expense  - Expense Tracker")
        return

    sys.exit(run_demo(args.demo))


if __name__ == "__main__":
    main()
