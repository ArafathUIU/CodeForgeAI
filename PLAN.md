# CodeForge: Multi-Agent AI Software Development Team

## Complete Implementation Blueprint

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [How CodeForge Works After Completion](#2-how-codeforge-works-after-completion)
3. [System Architecture](#3-system-architecture)
4. [Directory Structure](#4-directory-structure)
5. [The Six Agents](#5-the-six-agents)
6. [Core Orchestration Layer](#6-core-orchestration-layer)
7. [Implementation Phases](#7-implementation-phases)
8. [Commit Strategy & Targets](#8-commit-strategy--targets)
9. [Tech Stack](#9-tech-stack)
10. [Demo Projects](#10-demo-projects)
11. [Stretch Goals](#11-stretch-goals)

---

## 1. Project Overview

CodeForge is a multi-agent AI system where six specialized AI agents collaborate to build real software projects from natural language specifications. Unlike single-shot code generators, CodeForge manages the entire development lifecycle:

```
Requirements -> Architecture -> Implementation -> Testing -> Review -> Deployment
```

Each agent has a distinct role, communicates through structured protocols, and produces verifiable artifacts. The system includes human-in-the-loop approval gates at critical phases.

### How It Differs From Existing Tools

| Dimension | Typical AI Coding Tools | CodeForge |
|-----------|------------------------|-----------|
| Team Structure | Single AI does everything | Six specialized agents with distinct roles |
| Planning | No planning - code starts immediately | Structured phases: requirements -> design -> code -> test -> review -> deploy |
| Version Control | Code dumped in one batch | Real Git history with meaningful commits per agent |
| Testing | No automated testing | Dedicated test agent with five systematic test patterns |
| Security | No security review | Multi-layer security scanner with auto-fixes |
| Human Oversight | None or generic chat | Explicit approval gates at critical phases |

---

## 2. How CodeForge Works After Completion

### The Flow

1. **You open the Streamlit dashboard** in your browser (`http://localhost:8501`). It's a web UI, not a CLI tool or VS Code extension.

2. **You type a natural language specification** in the dashboard input box and hit submit.

3. **The agents talk to each other** behind the scenes, calling Ollama (running locally) for reasoning. You watch this live in the dashboard — agent statuses, message feed, artifacts being produced.

4. **The Code Writer agent creates real files on your disk** inside a directory you specify. It uses standard Python file operations (`open()`, `os.makedirs()`) — files appear in your filesystem just like if you created them manually.

5. **Every change is committed to a real Git repository** inside the project directory, with commit messages attributed to each agent.

### What You Get

| Step | What Happens | Where |
|------|-------------|-------|
| Dashboard runs | `streamlit run` on your machine | `localhost:8501` |
| Agents reason | Ollama API calls | Local Ollama server (`localhost:11434`) |
| Files created | Python writes to disk | Directory you specify |
| Git history built | Standard git operations | Inside the project directory |
| You review code | Open in VS Code or any editor | Like any normal project |

**The output is a normal, real project folder** — you can open it in any editor, inspect the code, run it, and deploy it. CodeForge doesn't hijack your editor; it produces projects that you then work with like any other codebase.

---

## 3. System Architecture

### High-Level Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Human Operator                        │
│                        │                                │
│                   Streamlit Dashboard                   │
│  ┌──────────┬──────────┬──────────┬──────────────────┐ │
│  │ Agent    │ Artifact │ Approval │ Message Bus      │ │
│  │ Monitor  │ Viewer   │ Gates    │ Feed             │ │
│  └──────────┴──────────┴──────────┴──────────────────┘ │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Orchestrator                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │            DAG Execution Engine                 │   │
│  │  Phase Gates · Transition Rules · Pipeline      │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Message Bus                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Priority Queue · Router · Delivery Tracker     │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Agent 1     │  │ Agent 2     │  │ Agent ...   │
│ Product Mgr │  │ Architect   │  │             │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         └───────────────┼───────────────┘
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Shared State Store                    │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Episodic Memory · Semantic Memory · Checkpoints │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Git Integration                       │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Repo Manager · Commit Manager · Branch Manager │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│                   Output Project                        │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Real files on disk · Git history · Docker · CI │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### Key Design Principles

1. **Structured Communication Only**: Agents never use free-form natural language with each other. Every message is a formal package with ID, type, priority, and structured payload.

2. **Shared Project Memory**: All agents access a centralized state store recording every decision, artifact, and conversation.

3. **Checkpoint and Recovery**: Every significant state change is persisted. If agents go off track, the system can roll back.

4. **Human-in-the-Loop**: Critical decisions require human approval via the dashboard.

5. **Git-Native Output**: Every agent contribution is a real Git commit with attribution.

---

## 4. Directory Structure

```
CodeForgeAI/
├── codeforge/                    # Main package
│   ├── __init__.py
│   │
│   ├── core/                     # Phase 1: Orchestration layer
│   │   ├── __init__.py
│   │   ├── message_protocol.py   # Message schema, types, validation
│   │   ├── message_bus.py        # Routing, delivery, priority queue
│   │   ├── state_store.py        # Shared project memory (episodic + semantic)
│   │   ├── checkpoint.py         # Snapshot and rollback system
│   │   ├── agent_registry.py     # Agent lifecycle and discoverability
│   │   ├── orchestrator.py       # Central coordinator and DAG engine
│   │   ├── conflict_resolver.py  # Mediation and escalation system
│   │   └── llm_client.py         # Ollama/LM Studio integration
│   │
│   ├── agents/                   # Phase 2-5: AI agents
│   │   ├── __init__.py
│   │   ├── base_agent.py         # Abstract base class for all agents
│   │   ├── product_manager/      # Phase 2
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── intent_parser.py
│   │   │   ├── clarification.py
│   │   │   └── prd_generator.py
│   │   ├── system_architect/     # Phase 2
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── tech_stack.py
│   │   │   ├── data_model.py
│   │   │   ├── api_designer.py
│   │   │   ├── file_tree.py
│   │   │   └── risk_assessor.py
│   │   ├── code_writer/          # Phase 3
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── structured_editor.py
│   │   │   ├── symbol_tracker.py
│   │   │   ├── skeleton_builder.py
│   │   │   ├── dependency_analyzer.py
│   │   │   ├── batch_implementer.py
│   │   │   └── syntax_validator.py
│   │   ├── test_engineer/        # Phase 4
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── pattern_generators.py
│   │   │   ├── fixture_builder.py
│   │   │   └── coverage_analyzer.py
│   │   ├── code_reviewer/        # Phase 4
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── analyzers.py
│   │   │   ├── auto_fixer.py
│   │   │   └── severity.py
│   │   └── devops/               # Phase 5
│   │       ├── __init__.py
│   │       ├── agent.py
│   │       ├── docker_generator.py
│   │       ├── compose_generator.py
│   │       └── cicd_generator.py
│   │
│   ├── artifacts/                # Typed data models
│   │   ├── __init__.py
│   │   ├── prd.py
│   │   ├── tech_spec.py
│   │   ├── source_code.py
│   │   ├── test_suite.py
│   │   ├── review_report.py
│   │   └── deployment.py
│   │
│   ├── prompts/                  # LLM prompt templates per agent
│   │   ├── __init__.py
│   │   ├── product_manager.py
│   │   ├── system_architect.py
│   │   ├── code_writer.py
│   │   ├── test_engineer.py
│   │   ├── code_reviewer.py
│   │   └── devops.py
│   │
│   ├── git/                      # Phase 5: Git integration
│   │   ├── __init__.py
│   │   ├── repo_manager.py
│   │   ├── commit_manager.py
│   │   └── branch_manager.py
│   │
│   ├── dashboard/                # Phase 6: Streamlit UI
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── views/
│   │   │   ├── __init__.py
│   │   │   ├── agent_monitor.py
│   │   │   ├── artifact_viewer.py
│   │   │   ├── approval_gates.py
│   │   │   ├── message_feed.py
│   │   │   └── git_timeline.py
│   │   └── utils.py
│   │
│   ├── plugins/                  # Phase 7: Plugin system (stretch)
│   │   ├── __init__.py
│   │   ├── loader.py
│   │   └── hooks.py
│   │
│   └── utils/                    # Shared utilities
│       ├── __init__.py
│       ├── config.py
│       ├── logging.py
│       ├── exceptions.py
│       └── validation.py
│
├── tests/                        # Test suite (mirrors codeforge/)
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_core/
│   │   ├── __init__.py
│   │   ├── test_message_protocol.py
│   │   ├── test_message_bus.py
│   │   ├── test_state_store.py
│   │   ├── test_checkpoint.py
│   │   ├── test_agent_registry.py
│   │   ├── test_orchestrator.py
│   │   ├── test_conflict_resolver.py
│   │   └── test_llm_client.py
│   ├── test_agents/
│   │   ├── __init__.py
│   │   ├── test_product_manager.py
│   │   ├── test_system_architect.py
│   │   ├── test_code_writer.py
│   │   ├── test_test_engineer.py
│   │   ├── test_code_reviewer.py
│   │   └── test_devops.py
│   ├── test_artifacts/
│   │   ├── __init__.py
│   │   └── test_artifact_models.py
│   ├── test_git/
│   │   ├── __init__.py
│   │   ├── test_repo_manager.py
│   │   ├── test_commit_manager.py
│   │   └── test_branch_manager.py
│   └── test_dashboard/
│       ├── __init__.py
│       └── test_views.py
│
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   └── user_guide.md
│
├── demos/
│   ├── expense_tracker_demo.py
│   └── todo_app_demo.py
│
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
└── PLAN.md
```

---

## 5. The Six Agents

### 5.1 Product Manager Agent

**Purpose**: Transform vague human input into a precise, structured Product Requirements Document (PRD).

**Process**:
1. Intent Parsing — identify core goal and implied features
2. Ambiguity Detection — flag unclear requirements
3. Scope Boundary Definition — determine what is out of scope
4. Edge Case Probing — identify unusual scenarios
5. Clarification Generation — produce specific questions for human
6. PRD Generation — produce formal document with user stories and acceptance criteria

**Output**: PRD with user stories in format: "As a [user], I want [capability], so that [benefit]"

### 5.2 System Architect Agent

**Purpose**: Convert PRD into implementable technical specification.

**Outputs**:
- Technology stack selection with justification and alternatives
- Data model design (tables, relationships, fields, indexes)
- API contract design (endpoints, methods, request/response formats)
- Complete folder/file tree
- Risk assessment with mitigation strategies

### 5.3 Code Writer Agent

**Purpose**: Implement code from the technical specification.

**Five Sequential Stages**:
1. Skeleton Creation — generate empty files matching Architect's file tree
2. Dependency Analysis — determine correct build order
3. Batch Implementation — generate code in structured chunks with precise edits
4. Syntax Validation — automated checks after each batch
5. Cross-File Consistency Check — verify all references resolve

**Key Innovation**: Uses structured "search and replace" edits rather than regenerating entire files.

### 5.4 Test Engineer Agent

**Purpose**: Generate meaningful tests proving code works.

**Five Test Patterns**:
1. Happy Path — normal operation with valid inputs
2. Boundary Cases — edge values and limits
3. Error Handling — expected failures handled gracefully
4. Concurrency — race conditions and simultaneous operations
5. Security — attack vectors and unauthorized access

### 5.5 Code Reviewer Agent

**Purpose**: Automated, multi-layered code review.

**Six Analysis Layers**:
1. Syntax Analysis — compilation, imports, type mismatches
2. Security Scanning — vulnerability patterns, injection risks
3. Style Compliance — PEP 8, naming conventions
4. Performance Analysis — N+1 queries, memory leaks, blocking ops
5. Maintainability Assessment — complexity, duplication, coupling
6. Architecture Compliance — structure vs. design, API contracts

### 5.6 DevOps Agent

**Purpose**: Prepare application for deployment.

**Outputs**:
- Multi-stage Dockerfile (build + production, non-root user)
- Docker Compose configuration (services, networking, health checks)
- CI/CD pipeline (GitHub Actions)
- Environment template with secret markers
- Deployment documentation

---

## 6. Core Orchestration Layer

### 6.1 Message Protocol

Every inter-agent message is a formal package:

```python
class Message:
    id: str              # UUID for traceability
    sender: str          # Agent identifier
    recipient: str       # Agent identifier or "orchestrator"
    type: MessageType    # Task, Artifact, Clarification, Blockage, Revision
    payload: dict        # Structured typed artifact
    priority: Priority   # Low, Normal, High, Critical
    requires_response: bool
    timeout_seconds: int
    timestamp: datetime
    correlation_id: str  # Links related messages
```

### 6.2 Message Types

- `TASK_ASSIGNMENT`: Orchestrator assigns work to an agent
- `ARTIFACT_SUBMISSION`: Agent submits completed work
- `CLARIFICATION_REQUEST`: Agent needs more information
- `BLOCKAGE_REPORT`: Agent cannot proceed
- `REVISION_REQUEST`: Reviewer or human requests changes
- `STATUS_UPDATE`: Periodic progress report
- `CONFLICT_ESCALATION`: Disagreement requiring resolution
- `APPROVAL_REQUEST`: Critical decision needs human input
- `APPROVAL_RESPONSE`: Human decision on approval
- `SYSTEM_EVENT`: Checkpoint, rollback, or system-level notification

### 6.3 Shared Project Memory

Two memory systems:

**Episodic Memory** — What happened during current project
- Decision log (what was decided, why, by whom)
- Artifact history (all versions of all documents)
- Conversation log (all messages between agents)

**Semantic Memory** — Patterns and lessons across projects
- Technology evaluations
- Common patterns
- Pitfalls encountered

### 6.4 Checkpoint System

Full project state snapshots enabling rollback:
- All artifacts at current version
- Agent state and memory
- Decision history
- Git repository state
- File workspace snapshot

### 6.5 Conflict Resolution

Priority hierarchy for resolving disagreements:
1. Security concerns override everything
2. Performance issues override style preferences
3. Style disputes auto-resolved via predefined rules
4. Fundamental disagreements escalate to human

---

## 7. Implementation Phases

### Phase 1 — Foundation & Orchestration Layer (Days 1-5, ~150 commits)
- Project scaffold and configuration
- LLM client (Ollama/LM Studio integration)
- Message protocol and message bus
- Shared state store (episodic + semantic)
- Checkpoint and recovery system
- Agent registry and base class
- Orchestrator with DAG engine
- Conflict resolver
- 25+ unit tests

### Phase 2 — PM & Architect Agents (Days 6-8, ~120 commits)
- Artifact data models (PRD, TechSpec, etc.)
- Product Manager: intent parser, clarification engine, PRD generator
- System Architect: tech stack selector, data model designer, API designer, file tree generator, risk assessor
- Prompt templates for both agents
- 25+ tests

### Phase 3 — Code Writer Agent (Days 9-10, ~100 commits)
- Structured editor engine (create/modify/delete/move)
- Cross-file symbol tracker
- Skeleton builder
- Dependency analyzer
- Batch implementation engine
- Syntax validator
- Agent integration with prompt templates
- 25+ tests

### Phase 4 — Test Engineer & Code Reviewer (Days 11-12, ~110 commits)
- Test Engineer: 5 pattern generators, fixture builder, coverage analyzer
- Code Reviewer: 6 analysis layers, auto-fixer, severity classifier
- Prompt templates
- 25+ tests

### Phase 5 — DevOps & Git Integration (Day 13, ~80 commits)
- Git repo/commit/branch managers
- Dockerfile generator (multi-stage)
- Docker Compose generator
- CI/CD generator (GitHub Actions)
- Environment template generator
- 20+ tests

### Phase 6 — Dashboard & Integration (Day 14, ~70 commits)
- Streamlit app shell
- Agent monitor view
- Artifact viewer (PRD, spec, code browser)
- Approval gate UI
- Message bus live feed
- Git timeline view
- End-to-end demo scenarios

### Phase 7 — Stretch Goals (Day 15, ~120 commits)
- Plugin system (agent plugin loader, custom registration, 2 example plugins)
- Multi-project semantic memory
- Webhook triggers (GitHub webhook listener)
- Demo runner with CLI
- Final documentation and README

---

## 8. Commit Strategy & Targets

### Commit Philosophy

Every commit should be meaningful — a single logical change that could be reviewed independently.

### Phase Commit Targets

| Phase | Scope | Files | Target Commits |
|-------|-------|-------|---------------|
| 1 — Foundation | Orchestration layer | ~64 | 150 |
| 2 — PM + Architect | Two agents | ~56 | 120 |
| 3 — Code Writer | Implementation agent | ~44 | 100 |
| 4 — Tester + Reviewer | QA agents | ~56 | 110 |
| 5 — DevOps + Git | Infrastructure | ~40 | 80 |
| 6 — Dashboard | UI + integration | ~39 | 70 |
| 7 — Stretch goals | Extras | ~30 | 120 |
| **Total** | | **~329** | **750** |

### Commit Naming Convention

```
[Phase.Milestone] Component: Brief description

Examples:
[1.3] Message Protocol: Define MessageType enum
[1.4] Message Bus: Implement priority queue
[2.1] Artifacts: Add PRD data model with UserStory
[3.2] Symbol Tracker: Add cross-file reference resolver
[4.5] Code Reviewer: Implement security scanner
```

---

## 9. Tech Stack

### Runtime
- **Language**: Python 3.11+
- **Web Framework**: FastAPI (internal API between dashboard and orchestration)
- **Dashboard**: Streamlit
- **Async**: asyncio, httpx

### AI/LLM
- **LLM Backend**: Ollama (local), configurable model (default: llama3.2)
- **API**: Ollama REST API at `localhost:11434`
- **Context**: Token-aware context window management

### Storage
- **State Store**: JSON file-based (Phase 1), SQLite (future)
- **Checkpoints**: JSON snapshots
- **Semantic Memory**: Simple embedding via Ollama

### Git
- **Library**: GitPython for repository operations

### DevOps Output
- **Containerization**: Docker (multi-stage builds)
- **Orchestration**: Docker Compose
- **CI/CD**: GitHub Actions YAML generation

### Testing
- **Framework**: pytest
- **Coverage**: pytest-cov
- **Mocking**: unittest.mock, pytest-asyncio

---

## 10. Demo Projects

Two pre-built demo scenarios will be included to demonstrate the full pipeline:

### Demo 1: Expense Tracker
- **Spec**: "Build a personal expense tracker where users can add expenses with categories, view summaries, and export data"
- **Stack**: FastAPI + SQLite + React (or simple HTML frontend)
- **Features**: CRUD expenses, categories, monthly summary, CSV export

### Demo 2: Todo Application
- **Spec**: "Create a task management app with projects, task priorities, due dates, and completion tracking"
- **Stack**: FastAPI + SQLite + Streamlit frontend
- **Features**: Projects, tasks with priorities, due dates, completion status, filtering

---

## 11. Stretch Goals

### Plugin System
- Dynamic agent registration
- Custom agent hooks for pipeline extension
- Two example plugins: Documentation Generator, Dependency Updater

### Multi-Project Memory
- Cross-project pattern extraction
- Lesson transfer between projects
- Technology evaluation database

### Webhook Triggers
- GitHub webhook listener
- Automatic pipeline trigger on push/PR
- Webhook configuration UI in dashboard

### Additional Features
- Demo runner CLI tool
- Architecture decision records (ADRs)
- Performance benchmarks
- Screenshot gallery for README

---

## Configuration

The system is configured via environment variables (see `.env.example`):

```env
# LLM Configuration
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_TEMPERATURE=0.2
OLLAMA_MAX_TOKENS=4096

# Agent Configuration
AGENT_TIMEOUT_SECONDS=300
MAX_RETRY_ATTEMPTS=3

# Storage
STATE_STORE_PATH=.codeforge/state
CHECKPOINT_PATH=.codeforge/checkpoints

# Git
GIT_AUTHOR_NAME=CodeForge AI
GIT_AUTHOR_EMAIL=codeforge@ai.local

# Dashboard
DASHBOARD_HOST=0.0.0.0
DASHBOARD_PORT=8501

# Approval
AUTO_APPROVE_STYLE_FIXES=true
APPROVAL_TIMEOUT_MINUTES=30
```

---

*Document prepared for CodeForge implementation — 750 commits across 7 phases in 15 days*
