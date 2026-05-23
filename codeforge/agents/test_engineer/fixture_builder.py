"""Fixture builder: generates test fixtures and mock data.

Creates reusable test fixtures, mock databases, and factory
functions for populating test data consistently.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Fixture:
    name: str
    scope: str
    code: str
    dependencies: list[str] = field(default_factory=list)


class FixtureBuilder:
    def build_model_fixture(
        self, entity_name: str, fields: list[dict]
    ) -> Fixture:
        field_defaults = []
        for f in fields:
            fname = f.get("name", "id")
            ftype = f.get("type", "str")
            if ftype == "int":
                field_defaults.append(f"    {fname}=1")
            elif ftype == "str":
                field_defaults.append(f'    {fname}="test_{fname}"')
            elif ftype == "bool":
                field_defaults.append(f"    {fname}=True")
            else:
                field_defaults.append(f"    {fname}=None")

        code = (
            f"import pytest\n\n"
            f"@pytest.fixture\n"
            f"def sample_{entity_name.lower()}():\n"
            f'    """Creates a sample {entity_name} for testing."""\n'
            f"    return {entity_name}(\n"
            + ",\n".join(field_defaults)
            + "\n    )\n"
        )

        return Fixture(
            name=f"sample_{entity_name.lower()}",
            scope="function",
            code=code,
        )

    def build_mock_fixture(self, target: str) -> Fixture:
        code = (
            f"import pytest\n"
            f"from unittest.mock import Mock\n\n"
            f"@pytest.fixture\n"
            f"def mock_{target}():\n"
            f'    """Provides a mocked {target} for isolated testing."""\n'
            f"    return Mock()\n"
        )
        return Fixture(
            name=f"mock_{target}",
            scope="function",
            code=code,
        )

    def build_db_fixture(self) -> Fixture:
        code = (
            "import pytest\n"
            "import sqlite3\n\n"
            "@pytest.fixture\n"
            "def test_db():\n"
            '    """In-memory database for testing."""\n'
            "    conn = sqlite3.connect(':memory:')\n"
            "    yield conn\n"
            "    conn.close()\n"
        )
        return Fixture(
            name="test_db",
            scope="function",
            code=code,
        )

    def build_app_fixture(self) -> Fixture:
        code = (
            "import pytest\n"
            "from fastapi.testclient import TestClient\n"
            "from app.main import app\n\n"
            "@pytest.fixture\n"
            "def client():\n"
            '    """Test client for the FastAPI application."""\n'
            "    return TestClient(app)\n"
        )
        return Fixture(
            name="client",
            scope="module",
            code=code,
        )

    def generate_conftest(self, fixtures: list[Fixture]) -> str:
        parts = ['"""Test fixtures for the project."""\n']
        for f in fixtures:
            parts.append(f"\n{f.code}\n")
        return "\n".join(parts)
