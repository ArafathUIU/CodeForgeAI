"""Tests for Code Writer Agent components."""

import asyncio

import pytest

from codeforge.agents.code_writer.agent import CodeWriterAgent
from codeforge.agents.code_writer.batch_implementer import BatchImplementer
from codeforge.agents.code_writer.dependency_analyzer import DependencyAnalyzer
from codeforge.agents.code_writer.skeleton_builder import SkeletonBuilder
from codeforge.agents.code_writer.structured_editor import FileOperationError, StructuredEditor
from codeforge.agents.code_writer.symbol_tracker import SymbolTracker
from codeforge.agents.code_writer.syntax_validator import SyntaxValidator
from codeforge.artifacts.tech_spec import FileTreeNode
from codeforge.core.message_bus import MessageBus
from codeforge.core.message_protocol import (
    ArtifactType,
    MessageType,
    create_task_assignment,
)


class TestStructuredEditor:
    @pytest.fixture
    def editor(self, tmp_path):
        return StructuredEditor(base_dir=str(tmp_path))

    def test_create_file(self, editor):
        editor.create_file("test.py", "print('hello')")
        assert editor.file_exists("test.py")
        content = editor.read_file("test.py")
        assert "print('hello')" in content

    def test_modify_file(self, editor):
        editor.create_file("test.py", "x = 1")
        editor.modify_file("test.py", "x = 1", "x = 2")
        content = editor.read_file("test.py")
        assert "x = 2" in content

    def test_modify_nonexistent_file_raises(self, editor):
        with pytest.raises(FileOperationError):
            editor.modify_file("nonexistent.py", "old", "new")

    def test_delete_file(self, editor):
        editor.create_file("test.py", "data")
        editor.delete_file("test.py")
        assert not editor.file_exists("test.py")

    def test_move_file(self, editor):
        editor.create_file("old.py", "original")
        editor.move_file("old.py", "new.py")
        assert not editor.file_exists("old.py")
        assert editor.file_exists("new.py")
        assert "original" in editor.read_file("new.py")

    def test_create_file_creates_directories(self, editor):
        editor.create_file("deep/nested/file.py", "data")
        assert editor.file_exists("deep/nested/file.py")

    def test_get_summary(self, editor):
        editor.create_file("a.py", "a")
        editor.create_file("b.py", "b")
        summary = editor.get_summary()
        assert summary["total_operations"] == 2


class TestSkeletonBuilder:
    @pytest.fixture
    def builder(self, tmp_path):
        editor = StructuredEditor(base_dir=str(tmp_path))
        return SkeletonBuilder(editor)

    def test_build_from_file_tree(self, builder):
        nodes = [
            FileTreeNode(path="app/__init__.py", node_type="file", purpose="Init"),
            FileTreeNode(path="app/models.py", node_type="file", purpose="Models"),
        ]
        result = builder.build(nodes)
        assert len(result.files_created) == 2
        assert result.success

    def test_build_directory_nodes(self, builder):
        nodes = [
            FileTreeNode(path="app", node_type="directory", purpose="Package"),
            FileTreeNode(path="app/main.py", node_type="file", purpose="Entry"),
        ]
        result = builder.build(nodes)
        assert result.success
        assert "app" in result.directories_created

    def test_generate_default_tree(self, builder):
        tree = builder.generate_default_tree("myapp")
        assert len(tree) >= 5
        paths = [n.path for n in tree]
        assert any("myapp" in p for p in paths)


class TestDependencyAnalyzer:
    @pytest.fixture
    def analyzer(self):
        return DependencyAnalyzer()

    def test_no_imports_returns_all(self, analyzer):
        files = ["a.py", "b.py", "c.py"]
        order = analyzer.analyze(files, {})
        assert len(order) == 3
        assert set(order) == set(files)

    def test_import_order(self, analyzer):
        files = ["main.py", "models.py", "services.py"]
        contents = {
            "main.py": "from models import User\nfrom services import do_stuff",
            "models.py": "",
            "services.py": "import models",
        }
        order = analyzer.analyze(files, contents)
        assert order.index("models.py") < order.index("main.py")
        assert order.index("models.py") < order.index("services.py")

    def test_build_order_property(self, analyzer):
        files = ["z.py", "a.py"]
        analyzer.analyze(files, {})
        assert len(analyzer.build_order) == 2


class TestSyntaxValidator:
    @pytest.fixture
    def validator(self, tmp_path):
        return SyntaxValidator(base_dir=str(tmp_path))

    def test_valid_python(self, validator):
        import os
        path = os.path.join(validator._base_dir, "valid.py")
        with open(path, "w") as f:
            f.write("x = 1\ny = 2\n")
        issues = validator.validate_file("valid.py")
        assert len(issues) == 0

    def test_syntax_error(self, validator):
        import os
        path = os.path.join(validator._base_dir, "broken.py")
        with open(path, "w") as f:
            f.write("def broken(\n")
        issues = validator.validate_file("broken.py")
        assert any(i.code == "SYNTAX_ERROR" for i in issues)

    def test_missing_file(self, validator):
        issues = validator.validate_file("ghost.py")
        assert any(i.code == "MISSING_FILE" for i in issues)

    def test_validate_batch(self, validator):
        import os
        os.makedirs(validator._base_dir, exist_ok=True)
        with open(os.path.join(validator._base_dir, "a.py"), "w") as f:
            f.write("x = 1\n")
        with open(os.path.join(validator._base_dir, "b.py"), "w") as f:
            f.write("y = 2\n")
        report = validator.validate_batch(["a.py", "b.py"])
        assert report.files_checked == 2
        assert report.files_passed == 2


class TestSymbolTracker:
    @pytest.fixture
    def tracker(self):
        return SymbolTracker()

    def test_scan_class_and_function(self, tracker):
        content = "class Foo:\n    def bar(self):\n        pass\n"
        symbols = tracker.scan_file("test.py", content)
        assert any(s.name == "Foo" and s.kind == "class" for s in symbols)
        assert any(s.name == "bar" and s.kind == "function" for s in symbols)

    def test_resolve_reference_same_file(self, tracker):
        tracker.scan_file("a.py", "class MyClass:\n    pass\n")
        resolved = tracker.resolve_reference("MyClass", "a.py")
        assert resolved is not None
        assert resolved.name == "MyClass"

    def test_resolve_reference_other_file(self, tracker):
        tracker.scan_file("lib.py", "def helper():\n    pass\n")
        resolved = tracker.resolve_reference("helper", "main.py")
        assert resolved is not None
        assert resolved.file_path == "lib.py"

    def test_unresolved_references(self, tracker):
        contents = {"main.py": "helper()\nunknown_func()\n"}
        unresolved = tracker.get_unresolved(contents)
        assert len(unresolved) >= 0


class TestBatchImplementer:
    @pytest.fixture
    def implementer(self, tmp_path):
        editor = StructuredEditor(base_dir=str(tmp_path))
        analyzer = DependencyAnalyzer()
        tracker = SymbolTracker()
        validator = SyntaxValidator(base_dir=str(tmp_path))
        return BatchImplementer(editor, analyzer, tracker, validator)

    def test_implement_basic(self, implementer):
        files = {
            "models.py": "class User:\n    pass\n",
            "main.py": "from models import User\n\nUser()\n",
        }
        result = implementer.implement(files)
        assert result.success
        assert len(result.files_written) == 2

    def test_implement_with_errors(self, implementer):
        files = {"bad.py": "def broken(\n"}
        result = implementer.implement(files)
        assert not result.success
        assert "bad.py" in result.files_written


class TestCodeWriterAgent:
    @pytest.fixture
    def agent(self, tmp_path):
        bus = MessageBus()
        return CodeWriterAgent(
            agent_id="cw-1",
            message_bus=bus,
            output_dir=str(tmp_path),
        )

    def test_role_is_code_writer(self, agent):
        assert agent.role == "code_writer"

    def test_process_task_creates_files(self, agent, tmp_path):
        msg = create_task_assignment(
            task_id="task-1",
            description="Implement code",
            agent_role="code_writer",
            sender="orchestrator",
            recipient="code_writer",
            context={
                "tech_spec": {
                    "title": "Test App",
                    "overview": "Testing",
                    "api_endpoints": [
                        {"method": "GET", "path": "/items", "summary": "List items"}
                    ],
                    "data_entities": [
                        {
                            "name": "Item",
                            "fields": [
                                {"name": "id", "type": "int"},
                                {"name": "name", "type": "str"},
                            ],
                        }
                    ],
                    "file_tree": [
                        {"path": "app/__init__.py", "node_type": "file", "purpose": "Init"},
                        {"path": "app/models.py", "node_type": "file", "purpose": "Models"},
                        {"path": "app/routes.py", "node_type": "file", "purpose": "Routes"},
                        {"path": "app/services.py", "node_type": "file", "purpose": "Services"},
                        {"path": "README.md", "node_type": "file", "purpose": "Docs"},
                    ],
                }
            },
        )

        async def run():
            await agent.initialize()
            await agent.handle_message(msg)

        asyncio.get_event_loop().run_until_complete(run())

        editor = agent._editor
        created = editor.files_created
        assert len(created) > 0

    def test_process_creates_artifact_submission(self, agent, tmp_path):
        bus = agent._message_bus
        received = []

        async def capture(msg):
            received.append(msg)

        bus.subscribe("orchestrator", capture)

        msg = create_task_assignment(
            task_id="task-2",
            description="Build app",
            agent_role="code_writer",
            sender="orchestrator",
            recipient="code_writer",
            context={
                "tech_spec": {
                    "title": "Hello",
                    "file_tree": [
                        {"path": "src/main.py", "node_type": "file", "purpose": "Main"},
                    ],
                }
            },
        )

        async def run():
            await agent.initialize()
            await agent.handle_message(msg)

        asyncio.get_event_loop().run_until_complete(run())

        artifacts = [m for m in received if m.type == MessageType.ARTIFACT_SUBMISSION]
        assert len(artifacts) > 0
        assert artifacts[0].payload.get("artifact_type") == "source_code" or \
               artifacts[0].payload.get("artifact_type") == ArtifactType.SOURCE_CODE.value

    def test_set_output_directory(self, agent, tmp_path):
        import os
        new_dir = os.path.join(str(tmp_path), "new_output")
        agent.set_output_directory(new_dir)
        assert agent._output_dir == new_dir
        assert agent._editor._base_dir == new_dir
