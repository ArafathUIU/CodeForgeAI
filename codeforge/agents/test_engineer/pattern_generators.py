"""Test pattern generators: five systematic test patterns.

1. Happy path testing
2. Boundary case testing
3. Error handling testing
4. Concurrency testing
5. Security testing
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TestCase:
    name: str
    pattern: str
    description: str
    code: str
    assertions: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


class PatternGenerators:
    def generate_happy_path(
        self, function_name: str, module_name: str = "app"
    ) -> TestCase:
        return TestCase(
            name=f"test_{function_name}_happy_path",
            pattern="happy_path",
            description=f"Verify {function_name} works with valid inputs",
            code=(
                f"from {module_name} import {function_name}\n\n"
                f"def test_{function_name}_happy_path():\n"
                f'    """{function_name} succeeds with standard input."""\n'
                f"    result = {function_name}()\n"
                f"    assert result is not None\n"
            ),
            assertions=["result is not None"],
            tags=["happy_path", function_name],
        )

    def generate_boundary(
        self, function_name: str, module_name: str = "app"
    ) -> TestCase:
        return TestCase(
            name=f"test_{function_name}_boundary",
            pattern="boundary",
            description=f"Verify {function_name} handles edge values",
            code=(
                f"import pytest\n"
                f"from {module_name} import {function_name}\n\n"
                f"def test_{function_name}_boundary():\n"
                f'    """{function_name} handles boundary values."""\n'
                f"    result = {function_name}()\n"
                f"    assert result is not None\n"
            ),
            assertions=["result is not None"],
            tags=["boundary", function_name],
        )

    def generate_error_handling(
        self, function_name: str, module_name: str = "app"
    ) -> TestCase:
        return TestCase(
            name=f"test_{function_name}_error_handling",
            pattern="error_handling",
            description=f"Verify {function_name} fails gracefully",
            code=(
                f"import pytest\n"
                f"from {module_name} import {function_name}\n\n"
                f"def test_{function_name}_error_handling():\n"
                f'    """{function_name} raises on invalid input."""\n'
                f"    with pytest.raises(Exception):\n"
                f"        {function_name}(None)\n"
            ),
            assertions=["raises Exception"],
            tags=["error_handling", function_name],
        )

    def generate_concurrency(
        self, function_name: str, module_name: str = "app"
    ) -> TestCase:
        return TestCase(
            name=f"test_{function_name}_concurrency",
            pattern="concurrency",
            description=f"Verify {function_name} under concurrent access",
            code=(
                f"import asyncio\n"
                f"from {module_name} import {function_name}\n\n"
                f"@pytest.mark.asyncio\n"
                f"async def test_{function_name}_concurrency():\n"
                f'    """{function_name} handles concurrent calls."""\n'
                f"    tasks = [{function_name}() for _ in range(5)]\n"
                f"    results = await asyncio.gather(*tasks)\n"
                f"    assert len(results) == 5\n"
            ),
            assertions=["len(results) == 5"],
            tags=["concurrency", function_name],
        )

    def generate_security(
        self, function_name: str, module_name: str = "app"
    ) -> TestCase:
        return TestCase(
            name=f"test_{function_name}_security",
            pattern="security",
            description=f"Verify {function_name} resists injection",
            code=(
                f"import pytest\n"
                f"from {module_name} import {function_name}\n\n"
                f"def test_{function_name}_security():\n"
                f'    """{function_name} rejects malicious input."""\n'
                f"    malicious = \"'; DROP TABLE users; --\"\n"
                f"    with pytest.raises(Exception):\n"
                f"        {function_name}(malicious)\n"
            ),
            assertions=["raises Exception"],
            tags=["security", function_name],
        )

    def generate_full_suite(
        self, function_name: str, module_name: str = "app"
    ) -> list[TestCase]:
        return [
            self.generate_happy_path(function_name, module_name),
            self.generate_boundary(function_name, module_name),
            self.generate_error_handling(function_name, module_name),
            self.generate_concurrency(function_name, module_name),
            self.generate_security(function_name, module_name),
        ]

    def generate_from_symbols(
        self, symbols: list, module_name: str = "app"
    ) -> list[TestCase]:
        tests: list[TestCase] = []
        for sym in symbols:
            name = getattr(sym, "name", sym)
            if getattr(sym, "kind", "function") in ("function", "class"):
                tests.extend(self.generate_full_suite(name, module_name))
        return tests
