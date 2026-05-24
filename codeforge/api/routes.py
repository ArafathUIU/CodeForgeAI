"""FastAPI routes for the CodeForge dashboard backend."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from codeforge.api.session import PipelineSession

router = APIRouter(prefix="/api")

_session: PipelineSession | None = None


class StartProjectRequest(BaseModel):
    specification: str
    output_directory: str = ""


class ApprovalRequest(BaseModel):
    approval_id: str
    decision: str
    comments: str = ""


def get_session() -> PipelineSession:
    global _session
    if _session is None:
        _session = PipelineSession()
    return _session


@router.get("/status")
async def get_status():
    session = get_session()
    return session.get_state()


@router.post("/start")
async def start_project(req: StartProjectRequest):
    session = get_session()
    try:
        project_id = await session.start(req.specification, req.output_directory)
        return {"project_id": project_id, "status": "started"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents")
async def get_agents():
    session = get_session()
    state = session.get_state()
    return state.get("agents", [])


@router.get("/artifacts")
async def get_artifacts():
    session = get_session()
    state = session.get_state()
    return state.get("artifacts", {})


@router.get("/messages")
async def get_messages(limit: int = 50):
    session = get_session()
    state = session.get_state()
    messages = state.get("messages", [])
    return messages[-limit:]


@router.post("/approve")
async def approve_artifact(req: ApprovalRequest):
    session = get_session()
    from codeforge.core.message_protocol import Message, MessageType

    msg = Message(
        sender="dashboard",
        recipient="orchestrator",
        type=MessageType.APPROVAL_RESPONSE,
        payload={
            "approval_id": req.approval_id,
            "decision": req.decision,
            "comments": req.comments,
        },
    )
    await session._orchestrator._message_bus.publish(msg)
    return {"status": "sent"}


@router.get("/pipeline")
async def get_pipeline():
    session = get_session()
    state = session.get_state()
    return {
        "phase": state.get("phase", "init"),
        "is_complete": state.get("is_complete", False),
        "errors": state.get("errors", []),
        "approval_gates": state.get("approval_gates", []),
    }
