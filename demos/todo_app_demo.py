"""[7.9] Demo: Add todo app demo scenario for end-to-end testing."""

TODO_APP_SPEC = {
    "name": "Todo App",
    "specification": (
        "Build a todo application with user authentication, "
        "CRUD operations for tasks, data export to CSV, "
        "and a dashboard view showing task statistics."
    ),
    "expected_phases": 7,
    "expected_files": [
        "app/__init__.py",
        "app/models.py",
        "app/routes.py",
        "app/services.py",
        "Dockerfile",
        "docker-compose.yml",
    ],
}
