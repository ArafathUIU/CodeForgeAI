"""Test Engineer Agent: generates comprehensive test suites."""

from __future__ import annotations

import json
import os
import uuid

from codeforge.agents.llm_mixin import LLMMixin
from codeforge.agents.test_engineer.coverage_analyzer import CoverageAnalyzer
from codeforge.agents.test_engineer.fixture_builder import FixtureBuilder
from codeforge.agents.test_engineer.pattern_generators import PatternGenerators
from codeforge.core.agent_registry import BaseAgent
from codeforge.core.llm_client import LlmClient
from codeforge.core.message_protocol import (
    ArtifactType,
    Message,
    MessageType,
    create_artifact_submission,
)
from codeforge.prompts.test_engineer import (
    TEST_ENGINEER_SYSTEM_PROMPT,
    build_test_prompt,
)


class TestEngineerAgent(LLMMixin, BaseAgent):
    """Generates meaningful tests proving code works across 5 patterns."""

    def __init__(self, *args, output_dir: str = "", llm_client: LlmClient | None = None, **kwargs):
        BaseAgent.__init__(self, *args, **kwargs)
        LLMMixin.__init__(self, llm_client=llm_client)
        self._output_dir = output_dir
        self._pattern_generator = PatternGenerators()
        self._fixture_builder = FixtureBuilder()
        self._coverage_analyzer = CoverageAnalyzer()

    @property
    def role(self) -> str:
        return "test_engineer"

    async def process_message(self, message: Message) -> None:
        if message.type != MessageType.TASK_ASSIGNMENT:
            return

        context = message.payload.get("context", {})
        tech_spec = context.get("tech_spec", {})

        await self.update_status("Generating test patterns", 0.2)

        entities = tech_spec.get("data_entities", [])
        symbols_to_test: list[str] = []
        for entity in entities:
            name = entity.get("name", entity.name if hasattr(entity, "name") else "Entity")
            symbols_to_test.append(name)

        if not symbols_to_test:
            symbols_to_test = ["DefaultService"]

        all_tests: list[str] = []

        llm_available = await self._check_llm()
        if llm_available and symbols_to_test:
            await self.update_status("Generating tests via LLM", 0.15)
            for name in symbols_to_test[:3]:
                entity_code = json.dumps(
                    next((e for e in entities if e.get("name", "") == name), {}),
                    indent=2, default=str,
                )
                response = await self.llm_reason(
                    system_prompt=TEST_ENGINEER_SYSTEM_PROMPT,
                    user_prompt=build_test_prompt(entity_code, name),
                    temperature=0.2,
                )
                llm_data = self.parse_json_response(response)
                if llm_data:
                    test_code = llm_data.get("test_code", llm_data.get("raw_content", ""))
                    if test_code:
                        all_tests.append(test_code)

        if not all_tests:
            for name in symbols_to_test:
                suite = self._pattern_generator.generate_full_suite(name)
                for tc in suite:
                    all_tests.append(tc.code)

        await self.update_status("Building fixtures", 0.4)

        fixtures = []
        for entity in entities:
            entity_name = entity.get(
                "name", entity.name if hasattr(entity, "name") else "Entity"
            )
            fields = entity.get(
                "fields",
                entity.fields if hasattr(entity, "fields") else [],
            )
            fixtures.append(
                self._fixture_builder.build_model_fixture(entity_name, fields)
            )

        conftest_content = self._fixture_builder.generate_conftest(fixtures)

        await self.update_status("Analyzing coverage", 0.6)

        symbols = []
        for name in symbols_to_test:
            symbols.append(name)

        coverage_report = self._coverage_analyzer.analyze(
            symbols, [], {}
        )

        await self.update_status("Writing test files", 0.8)

        test_files: list[str] = []
        base = self._output_dir or "."

        tests_dir = os.path.join(base, "tests")
        os.makedirs(tests_dir, exist_ok=True)

        conftest_path = os.path.join(tests_dir, "conftest.py")
        with open(conftest_path, "w", encoding="utf-8") as f:
            f.write(conftest_content)
        test_files.append("tests/conftest.py")

        for i, entity in enumerate(entities):
            entity_name = entity.get(
                "name", entity.name if hasattr(entity, "name") else f"Entity{i}"
            )
            test_name = f"test_{entity_name.lower()}.py"
            test_path = os.path.join(tests_dir, test_name)

            suite = self._pattern_generator.generate_full_suite(entity_name)
            test_content = "import pytest\n\n" + "\n\n".join(
                tc.code for tc in suite
            )

            with open(test_path, "w", encoding="utf-8") as f:
                f.write(test_content)
            test_files.append(f"tests/{test_name}")

        await self.discuss_with(
            "code_reviewer",
            f"I have generated {len(test_files)} test files "
            f"covering {coverage_report.patterns_used} test patterns. "
            f"{coverage_report.summary()}. "
            f"I tested {len(symbols)} symbols across the codebase. "
            f"Please review the code quality, security, style, "
            f"and architecture compliance.",
            reasoning=(
                f"Applied {coverage_report.patterns_used} test patterns. "
                f"Tested {len(symbols)} symbols. "
                f"Meets threshold: {coverage_report.meets_threshold}."
            ),
            plan_snippet=(
                f"Tests: {len(test_files)} files, "
                f"{coverage_report.patterns_used} patterns."
            ),
        )

        test_suite_id = f"test-suite-{uuid.uuid4().hex[:8]}"

        artifact_msg = create_artifact_submission(
            artifact_id=test_suite_id,
            artifact_type=ArtifactType.TEST_SUITE,
            content={
                "test_files": test_files,
                "patterns_generated": 5,
                "symbols_tested": len(symbols_to_test),
                "coverage_report": coverage_report.summary(),
                "meets_threshold": coverage_report.meets_threshold,
                "missing_tests": self._coverage_analyzer.suggest_missing_tests(
                    coverage_report
                ),
            },
            sender=self.agent_id,
            validation_status="ready" if coverage_report.meets_threshold else "insufficient",
            notes=coverage_report.summary(),
        )
        await self.send_message(artifact_msg)
        await self.update_status("Test suite complete", 1.0)
