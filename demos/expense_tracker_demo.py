"""[7.10] Demo: Add expense tracker demo scenario."""

EXPENSE_TRACKER_SPEC = {
    "name": "Expense Tracker",
    "specification": (
        "Build an expense tracking application with category "
        "management, monthly budget alerts, receipt image upload, "
        "and spending analytics dashboard."
    ),
    "expected_phases": 7,
    "expected_files": [
        "app/__init__.py",
        "app/models.py",
        "app/routes.py",
        "app/services.py",
        "app/analytics.py",
        "Dockerfile",
    ],
}
