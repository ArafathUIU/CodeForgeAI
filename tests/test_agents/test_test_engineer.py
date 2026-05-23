"""Tests for Test Engineer Agent components."""


import pytest

from codeforge.agents.test_engineer.coverage_analyzer import CoverageAnalyzer
from codeforge.agents.test_engineer.fixture_builder import FixtureBuilder
from codeforge.agents.test_engineer.pattern_generators import PatternGenerators


class TestPatternGenerators:
    @pytest.fixture
    def gen(self):
        return PatternGenerators()

    def test_happy_path(self, gen):
        tc = gen.generate_happy_path("do_work")
        assert tc.pattern == "happy_path"
        assert "def test_do_work_happy_path" in tc.code

    def test_boundary(self, gen):
        tc = gen.generate_boundary("process")
        assert tc.pattern == "boundary"
        assert "process" in tc.code

    def test_error_handling(self, gen):
        tc = gen.generate_error_handling("validate")
        assert tc.pattern == "error_handling"
        assert "pytest.raises" in tc.code

    def test_concurrency(self, gen):
        tc = gen.generate_concurrency("async_op")
        assert tc.pattern == "concurrency"
        assert "asyncio" in tc.code

    def test_security(self, gen):
        tc = gen.generate_security("login")
        assert tc.pattern == "security"
        assert "DROP TABLE" in tc.code

    def test_full_suite(self, gen):
        suite = gen.generate_full_suite("my_func")
        assert len(suite) == 5
        patterns = {tc.pattern for tc in suite}
        assert patterns == {"happy_path", "boundary", "error_handling",
                            "concurrency", "security"}

    def test_generate_from_symbols(self, gen):
        symbols = [
            type("Sym", (), {"name": "LoginService", "kind": "class"}),
            type("Sym", (), {"name": "do_stuff", "kind": "function"}),
        ]
        suite = gen.generate_from_symbols(symbols)
        assert len(suite) == 10


class TestFixtureBuilder:
    @pytest.fixture
    def builder(self):
        return FixtureBuilder()

    def test_build_model_fixture(self, builder):
        fields = [
            {"name": "id", "type": "int"},
            {"name": "name", "type": "str"},
        ]
        fixture = builder.build_model_fixture("User", fields)
        assert "sample_user" in fixture.name
        assert "User(" in fixture.code
        assert "id=1" in fixture.code

    def test_build_mock_fixture(self, builder):
        fixture = builder.build_mock_fixture("database")
        assert "mock_database" in fixture.name
        assert "Mock()" in fixture.code

    def test_build_db_fixture(self, builder):
        fixture = builder.build_db_fixture()
        assert "test_db" in fixture.name
        assert "sqlite3" in fixture.code

    def test_generate_conftest(self, builder):
        fixtures = [
            builder.build_model_fixture("Item", [{"name": "id", "type": "int"}]),
        ]
        content = builder.generate_conftest(fixtures)
        assert "sample_item" in content
        assert "pytest.fixture" in content


class TestCoverageAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return CoverageAnalyzer()

    def test_full_coverage(self, analyzer):
        symbols = ["User", "Item", "Order"]
        test_content = {"test_all.py": "def test_user(): pass\nItem is tested\nOrder works"}
        report = analyzer.analyze(symbols, ["test_all.py"], test_content)
        assert report.total_symbols == 3
        assert report.tested_symbols == 3

    def test_partial_coverage(self, analyzer):
        symbols = ["User", "Item"]
        test_content = {"test_users.py": "def test_user(): pass"}
        report = analyzer.analyze(symbols, ["test_users.py"], test_content)
        assert report.tested_symbols == 1
        assert report.untested_symbols == 1

    def test_meets_threshold(self, analyzer):
        symbols = [str(i) for i in range(100)]
        test_content = {"test.py": " ".join(str(i) for i in range(85))}
        report = analyzer.analyze(symbols, ["test.py"], test_content)
        assert report.meets_threshold

    def test_suggest_missing_tests(self, analyzer):
        symbols = ["Foo", "Bar"]
        test_content = {"test.py": "Foo"}
        report = analyzer.analyze(symbols, ["test.py"], test_content)
        suggestions = analyzer.suggest_missing_tests(report)
        assert any("Bar" in s for s in suggestions)
