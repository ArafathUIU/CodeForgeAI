# CodeForge AI

Multi-Agent AI Software Development Team — six specialized AI agents collaborate to build real software projects from natural language specifications.

## Architecture

```
Requirements -> Architecture -> Implementation -> Testing -> Review -> Deployment
```

## Agents

| Agent | Role | Phase |
|-------|------|-------|
| Product Manager | Intent parsing, PRD generation | Requirements |
| System Architect | Tech stack, data model, API design | Architecture |
| Code Writer | Structured file creation, batch implementation | Implementation |
| Test Engineer | 5-pattern test generation, coverage analysis | Testing |
| Code Reviewer | 6-layer review, auto-fix, severity classification | Review |
| DevOps | Docker, Compose, CI/CD generation | Deployment |

## Quick Start

```bash
pip install -e ".[dev]"
cp .env.example .env
pytest
```

## Project Structure

```
codeforge/
  core/         # Orchestration, message bus, state store, LLM client
  agents/       # Six specialized AI agents
  artifacts/    # PRD, TechSpec data models
  prompts/      # LLM prompt templates
  utils/        # Config, logging, validation
  dashboard/    # Streamlit UI (Phase 6)
  git/          # Git integration (Phase 5)
  plugins/      # Plugin system (Phase 7)
tests/          # Unit and integration tests
```

## Configuration

Set environment variables or use `.env`:

```
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

## Status

Phases 1-4 complete. See [PROGRESS.md](PROGRESS.md) for details.
