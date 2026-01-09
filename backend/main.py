"""FastAPI backend for the Agentic Grants Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uuid
import json
import asyncio

from . import storage
from .config import CORS_ORIGINS, API_HOST, API_PORT
from .models import (
    SubmitApplicationRequest,
    HumanDecisionRequest,
    RecordOutcomeRequest,
    DecisionStatus,
    GrantOutcome,
    LearningEvent,
    MilestoneOutcome,
)
from .grants_council import run_grants_council, run_grants_council_streaming
from .agents import get_all_agents

# Keep legacy imports for backwards compatibility
from .council import (
    run_full_council,
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
    augment_query_with_urls,
)

app = FastAPI(
    title="Agentic Grants Council API",
    description="AI-powered grant application evaluation system with persistent agent identities",
    version="2.0.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# Pydantic Models for API
# ============================================================================

class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    messages: List[Dict[str, Any]]


# ============================================================================
# Health & Info Endpoints
# ============================================================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "Agentic Grants Council API",
        "version": "2.0.0",
    }


@app.get("/api/agents")
async def list_agents():
    """List all council agents and their roles."""
    agents = get_all_agents()
    return [
        {
            "id": a.id,
            "name": a.name,
            "role": a.role,
            "description": a.description,
            "model": a.model,
        }
        for a in agents
    ]


# ============================================================================
# Application Endpoints
# ============================================================================

@app.get("/api/applications")
async def list_applications(status: Optional[str] = None, limit: int = 100):
    """List all grant applications."""
    applications = await storage.list_applications(status=status, limit=limit)
    return applications


@app.post("/api/applications")
async def submit_application(request: SubmitApplicationRequest):
    """
    Submit a new grant application for evaluation.

    The application will be parsed, evaluated by all agents,
    deliberated, and a decision will be made.
    """
    # Fetch content from any URLs in the request
    content = await augment_query_with_urls(request.content)

    result = await run_grants_council(
        raw_content=content,
        source=request.source,
        source_id=request.source_id,
    )

    return result


@app.post("/api/applications/stream")
async def submit_application_stream(request: SubmitApplicationRequest):
    """
    Submit a new grant application with streaming updates.

    Returns Server-Sent Events as each stage completes.
    """
    # Fetch content from any URLs in the request
    content = await augment_query_with_urls(request.content)

    async def event_generator():
        async for event in run_grants_council_streaming(
            raw_content=content,
            source=request.source,
            source_id=request.source_id,
        ):
            yield f"data: {json.dumps(event, default=str)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


@app.get("/api/applications/{application_id}")
async def get_application(application_id: str):
    """Get a specific application with all its evaluation data."""
    application = await storage.get_application(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    # Get related data
    evaluations = await storage.get_evaluations_for_application(application_id)
    deliberation = await storage.get_deliberation(application_id)
    decision = await storage.get_decision(application_id)
    outcome = await storage.get_outcome(application_id)

    return {
        "application": application.model_dump(),
        "evaluations": [e.model_dump() for e in evaluations],
        "deliberation": deliberation.model_dump() if deliberation else None,
        "decision": decision.model_dump() if decision else None,
        "outcome": outcome.model_dump() if outcome else None,
    }


@app.post("/api/applications/{application_id}/decision")
async def record_human_decision(application_id: str, request: HumanDecisionRequest):
    """
    Record a human decision for an application.

    Used when:
    - Application was routed to human review
    - Human is overriding council decision
    """
    from datetime import datetime

    application = await storage.get_application(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    # Record the decision
    was_override = application.status in [
        DecisionStatus.AUTO_APPROVED,
        DecisionStatus.AUTO_REJECTED,
    ]

    if request.decision == "approve":
        application.status = DecisionStatus.HUMAN_APPROVED
    else:
        application.status = DecisionStatus.HUMAN_REJECTED

    application.final_decision = request.decision
    application.decision_rationale = request.rationale
    application.decided_at = datetime.utcnow()
    application.decided_by = "human"
    application.was_overridden = was_override
    if was_override:
        application.override_reason = request.rationale

    await storage.save_application(application)

    # Create learning event if this was an override
    if was_override:
        event = LearningEvent(
            id=str(uuid.uuid4()),
            event_type="override",
            application_id=application_id,
            description=f"Human overrode council decision: {application.status.value} -> {request.decision}",
            context={
                "original_decision": application.status.value,
                "new_decision": request.decision,
                "rationale": request.rationale,
            },
        )
        await storage.save_learning_event(event)

    return {"status": "ok", "application_id": application_id}


@app.post("/api/applications/{application_id}/outcome")
async def record_outcome(application_id: str, request: RecordOutcomeRequest):
    """
    Record the outcome of a funded grant.

    This triggers learning events that help agents improve.
    """
    application = await storage.get_application(application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    # Create outcome record
    outcome = GrantOutcome(
        application_id=application_id,
        completed=request.completed,
        completion_percentage=request.completion_percentage,
        milestone_outcomes=request.milestone_outcomes,
        impact_assessment=request.impact_assessment,
        quality_score=request.quality_score,
        notes=request.notes,
    )
    await storage.save_outcome(outcome)

    # Create learning event
    event = LearningEvent(
        id=str(uuid.uuid4()),
        event_type="outcome",
        application_id=application_id,
        description=f"Grant outcome recorded: {'completed' if request.completed else 'incomplete'} ({request.completion_percentage}%)",
        context={
            "completed": request.completed,
            "completion_percentage": request.completion_percentage,
            "quality_score": request.quality_score,
        },
    )
    await storage.save_learning_event(event)

    return {"status": "ok", "application_id": application_id}


# ============================================================================
# Team Endpoints
# ============================================================================

@app.get("/api/teams")
async def list_teams(limit: int = 100):
    """List all team profiles."""
    teams = await storage.list_teams(limit=limit)
    return teams


@app.get("/api/teams/{team_id}")
async def get_team(team_id: str):
    """Get a specific team profile."""
    team = await storage.get_team_by_id(team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="Team not found")
    return team.model_dump()


# ============================================================================
# Observation Endpoints
# ============================================================================

@app.get("/api/observations")
async def list_observations(agent_id: Optional[str] = None, status: Optional[str] = None):
    """List agent observations with optional filtering."""
    observations = await storage.list_observations(agent_id=agent_id, status=status)
    return [o.model_dump() for o in observations]


@app.post("/api/observations/{observation_id}/approve")
async def approve_observation(observation_id: str):
    """Approve a draft observation to make it active."""
    # Load observation
    observations = await storage.list_observations()
    observation = next((o for o in observations if o.id == observation_id), None)

    if observation is None:
        raise HTTPException(status_code=404, detail="Observation not found")

    from .models import ValidationStatus
    observation.status = ValidationStatus.ACTIVE
    await storage.save_observation(observation)

    return {"status": "ok", "observation_id": observation_id}


@app.delete("/api/observations/{observation_id}")
async def delete_observation(observation_id: str):
    """Delete or deprecate an observation."""
    observations = await storage.list_observations()
    observation = next((o for o in observations if o.id == observation_id), None)

    if observation is None:
        raise HTTPException(status_code=404, detail="Observation not found")

    from .models import ValidationStatus
    observation.status = ValidationStatus.DEPRECATED
    await storage.save_observation(observation)

    return {"status": "ok", "observation_id": observation_id}


# ============================================================================
# Legacy Endpoints (Backwards Compatibility with Original LLM Council)
# ============================================================================

@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only) - Legacy endpoint."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation - Legacy endpoint."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages - Legacy endpoint."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process - Legacy endpoint.
    Returns the complete response with all stages.
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(conversation["messages"]) == 0
    storage.add_user_message(conversation_id, request.content)

    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process - Legacy endpoint.
    Returns Server-Sent Events as each stage completes.
    """
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            storage.add_user_message(conversation_id, request.content)

            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=API_HOST, port=API_PORT)
