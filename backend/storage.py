"""Storage layer for the Grants Council.

Provides an abstraction over storage backends.
Currently supports JSON file storage for development.
Can be extended to PostgreSQL for production.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR

from .models import (
    Application,
    ParsedApplication,
    TeamProfile,
    TeamMatch,
    AgentObservation,
    AgentEvaluation,
    Deliberation,
    CouncilDecision,
    GrantOutcome,
    LearningEvent,
)


# ============================================================================
# Directory Setup
# ============================================================================

def ensure_data_dirs():
    """Ensure all data directories exist."""
    dirs = [
        DATA_DIR,
        f"{DATA_DIR}/applications",
        f"{DATA_DIR}/teams",
        f"{DATA_DIR}/evaluations",
        f"{DATA_DIR}/deliberations",
        f"{DATA_DIR}/decisions",
        f"{DATA_DIR}/observations",
        f"{DATA_DIR}/outcomes",
        f"{DATA_DIR}/learning_events",
        f"{DATA_DIR}/conversations",  # Keep for backwards compatibility
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)


# ============================================================================
# Application Storage
# ============================================================================

async def save_application(application: Application) -> None:
    """Save an application to storage."""
    ensure_data_dirs()
    path = f"{DATA_DIR}/applications/{application.id}.json"
    with open(path, 'w') as f:
        json.dump(application.model_dump(mode='json'), f, indent=2, default=str)


async def get_application(application_id: str) -> Optional[Application]:
    """Load an application from storage."""
    path = f"{DATA_DIR}/applications/{application_id}.json"
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        data = json.load(f)
        return Application(**data)


async def list_applications(
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Dict[str, Any]]:
    """List applications with optional filtering."""
    ensure_data_dirs()
    apps_dir = f"{DATA_DIR}/applications"
    applications = []

    for filename in os.listdir(apps_dir):
        if filename.endswith('.json'):
            path = os.path.join(apps_dir, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                if status is None or data.get('status') == status:
                    applications.append({
                        "id": data["id"],
                        "created_at": data["created_at"],
                        "status": data.get("status", "pending"),
                        "project_name": data.get("parsed", {}).get("project_name", "Unknown") if data.get("parsed") else "Unknown",
                        "team_name": data.get("parsed", {}).get("team_name", "Unknown") if data.get("parsed") else "Unknown",
                        "requested_amount": data.get("parsed", {}).get("requested_amount", 0) if data.get("parsed") else 0,
                    })

    # Sort by creation time, newest first
    applications.sort(key=lambda x: x["created_at"], reverse=True)
    return applications[:limit]


# ============================================================================
# Team Storage
# ============================================================================

async def save_team(team: TeamProfile) -> None:
    """Save a team profile to storage."""
    ensure_data_dirs()
    path = f"{DATA_DIR}/teams/{team.id}.json"
    with open(path, 'w') as f:
        json.dump(team.model_dump(mode='json'), f, indent=2, default=str)


async def get_team_by_id(team_id: str) -> Optional[TeamProfile]:
    """Load a team profile by ID."""
    path = f"{DATA_DIR}/teams/{team_id}.json"
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        data = json.load(f)
        return TeamProfile(**data)


async def find_matching_team(parsed: ParsedApplication) -> Optional[TeamMatch]:
    """
    Attempt to find a matching team for an application.

    Matching strategies:
    1. Exact wallet match (definitive)
    2. Fuzzy name match
    3. Member overlap

    Returns TeamMatch with confidence and match type.
    """
    ensure_data_dirs()
    teams_dir = f"{DATA_DIR}/teams"

    if not os.path.exists(teams_dir):
        return None

    best_match = None
    best_confidence = 0.0

    for filename in os.listdir(teams_dir):
        if filename.endswith('.json'):
            path = os.path.join(teams_dir, filename)
            with open(path, 'r') as f:
                team_data = json.load(f)
                team = TeamProfile(**team_data)

            match_result = _check_team_match(parsed, team)
            if match_result and match_result["confidence"] > best_confidence:
                best_confidence = match_result["confidence"]
                best_match = TeamMatch(
                    matched_team_id=team.id,
                    match_confidence=match_result["confidence"],
                    match_type=match_result["type"],
                    requires_confirmation=match_result["confidence"] < 0.9,
                    match_evidence=match_result["evidence"],
                )

    return best_match


def _check_team_match(parsed: ParsedApplication, team: TeamProfile) -> Optional[Dict[str, Any]]:
    """Check if a parsed application matches a team profile."""
    evidence = []
    confidence = 0.0
    match_type = "none"

    # Check wallet address match (definitive)
    if parsed.wallet_address and parsed.wallet_address.lower() in [w.lower() for w in team.wallet_addresses]:
        return {
            "confidence": 1.0,
            "type": "exact_wallet",
            "evidence": [f"Wallet address {parsed.wallet_address} matches team wallet"],
        }

    # Check team name match
    parsed_name_lower = parsed.team_name.lower().strip()
    team_names = [team.canonical_name.lower()] + [a.lower() for a in team.aliases]

    for name in team_names:
        if parsed_name_lower == name:
            confidence = max(confidence, 0.9)
            match_type = "fuzzy_name"
            evidence.append(f"Team name '{parsed.team_name}' matches '{name}'")
            break
        elif parsed_name_lower in name or name in parsed_name_lower:
            confidence = max(confidence, 0.7)
            match_type = "fuzzy_name"
            evidence.append(f"Team name '{parsed.team_name}' partially matches '{name}'")

    # Check member overlap
    parsed_member_names = [m.name.lower() for m in parsed.team_members]
    team_member_names = [m.name.lower() for m in team.members]

    overlap = set(parsed_member_names) & set(team_member_names)
    if overlap:
        overlap_ratio = len(overlap) / max(len(parsed_member_names), len(team_member_names))
        if overlap_ratio >= 0.5:
            confidence = max(confidence, 0.8)
            match_type = "member_overlap"
            evidence.append(f"Member overlap: {', '.join(overlap)}")
        elif overlap_ratio >= 0.3:
            confidence = max(confidence, 0.6)
            match_type = "member_overlap"
            evidence.append(f"Some member overlap: {', '.join(overlap)}")

    if confidence > 0:
        return {
            "confidence": confidence,
            "type": match_type,
            "evidence": evidence,
        }

    return None


async def list_teams(limit: int = 100) -> List[Dict[str, Any]]:
    """List all team profiles."""
    ensure_data_dirs()
    teams_dir = f"{DATA_DIR}/teams"
    teams = []

    if not os.path.exists(teams_dir):
        return teams

    for filename in os.listdir(teams_dir):
        if filename.endswith('.json'):
            path = os.path.join(teams_dir, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                teams.append({
                    "id": data["id"],
                    "canonical_name": data["canonical_name"],
                    "grants_received": data.get("grants_received", 0),
                    "grants_completed": data.get("grants_completed", 0),
                    "total_funding_received": data.get("total_funding_received", 0),
                })

    return teams[:limit]


# ============================================================================
# Evaluation Storage
# ============================================================================

async def save_evaluation(evaluation: AgentEvaluation) -> None:
    """Save an evaluation to storage."""
    ensure_data_dirs()
    path = f"{DATA_DIR}/evaluations/{evaluation.id}.json"
    with open(path, 'w') as f:
        json.dump(evaluation.model_dump(mode='json'), f, indent=2, default=str)


async def get_evaluations_for_application(application_id: str) -> List[AgentEvaluation]:
    """Get all evaluations for an application."""
    ensure_data_dirs()
    evals_dir = f"{DATA_DIR}/evaluations"
    evaluations = []

    if not os.path.exists(evals_dir):
        return evaluations

    for filename in os.listdir(evals_dir):
        if filename.endswith('.json'):
            path = os.path.join(evals_dir, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                if data.get('application_id') == application_id:
                    evaluations.append(AgentEvaluation(**data))

    return evaluations


# ============================================================================
# Deliberation Storage
# ============================================================================

async def save_deliberation(deliberation: Deliberation) -> None:
    """Save a deliberation record."""
    ensure_data_dirs()
    path = f"{DATA_DIR}/deliberations/{deliberation.application_id}.json"
    with open(path, 'w') as f:
        json.dump(deliberation.model_dump(mode='json'), f, indent=2, default=str)


async def get_deliberation(application_id: str) -> Optional[Deliberation]:
    """Get deliberation for an application."""
    path = f"{DATA_DIR}/deliberations/{application_id}.json"
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        data = json.load(f)
        return Deliberation(**data)


# ============================================================================
# Decision Storage
# ============================================================================

async def save_decision(decision: CouncilDecision) -> None:
    """Save a council decision."""
    ensure_data_dirs()
    path = f"{DATA_DIR}/decisions/{decision.application_id}.json"
    with open(path, 'w') as f:
        json.dump(decision.model_dump(mode='json'), f, indent=2, default=str)


async def get_decision(application_id: str) -> Optional[CouncilDecision]:
    """Get decision for an application."""
    path = f"{DATA_DIR}/decisions/{application_id}.json"
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        data = json.load(f)
        return CouncilDecision(**data)


# ============================================================================
# Observation Storage
# ============================================================================

async def save_observation(observation: AgentObservation) -> None:
    """Save an agent observation."""
    ensure_data_dirs()
    path = f"{DATA_DIR}/observations/{observation.id}.json"
    with open(path, 'w') as f:
        json.dump(observation.model_dump(mode='json'), f, indent=2, default=str)


async def get_relevant_observations(
    agent_id: str,
    tags: List[str],
    limit: int = 5,
) -> List[AgentObservation]:
    """
    Get relevant observations for an agent based on tags.

    Returns observations that match any of the provided tags,
    sorted by relevance (number of matching tags) and confidence.
    """
    ensure_data_dirs()
    obs_dir = f"{DATA_DIR}/observations"
    observations = []

    if not os.path.exists(obs_dir):
        return observations

    for filename in os.listdir(obs_dir):
        if filename.endswith('.json'):
            path = os.path.join(obs_dir, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                if data.get('agent_id') == agent_id and data.get('status') == 'active':
                    obs = AgentObservation(**data)
                    # Calculate relevance based on tag overlap
                    tag_overlap = len(set(obs.tags) & set(tags))
                    if tag_overlap > 0:
                        observations.append((tag_overlap, obs))

    # Sort by tag overlap (desc) then confidence
    observations.sort(key=lambda x: (x[0], x[1].confidence.value), reverse=True)

    return [obs for _, obs in observations[:limit]]


async def list_observations(
    agent_id: Optional[str] = None,
    status: Optional[str] = None,
) -> List[AgentObservation]:
    """List observations with optional filtering."""
    ensure_data_dirs()
    obs_dir = f"{DATA_DIR}/observations"
    observations = []

    if not os.path.exists(obs_dir):
        return observations

    for filename in os.listdir(obs_dir):
        if filename.endswith('.json'):
            path = os.path.join(obs_dir, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                if agent_id and data.get('agent_id') != agent_id:
                    continue
                if status and data.get('status') != status:
                    continue
                observations.append(AgentObservation(**data))

    return observations


# ============================================================================
# Similar Applications (Vector Search Placeholder)
# ============================================================================

async def get_similar_applications(
    application_id: str,
    parsed: ParsedApplication,
    limit: int = 3,
) -> List[Dict[str, Any]]:
    """
    Get similar applications for context.

    TODO: Implement actual vector similarity search.
    For now, returns empty list as placeholder.

    In production, this would:
    1. Embed the application description
    2. Query vector database for similar embeddings
    3. Return applications with outcomes
    """
    # Placeholder - return empty list
    # In production, implement vector similarity search
    return []


# ============================================================================
# Outcome Storage
# ============================================================================

async def save_outcome(outcome: GrantOutcome) -> None:
    """Save a grant outcome."""
    ensure_data_dirs()
    path = f"{DATA_DIR}/outcomes/{outcome.application_id}.json"
    with open(path, 'w') as f:
        json.dump(outcome.model_dump(mode='json'), f, indent=2, default=str)


async def get_outcome(application_id: str) -> Optional[GrantOutcome]:
    """Get outcome for an application."""
    path = f"{DATA_DIR}/outcomes/{application_id}.json"
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        data = json.load(f)
        return GrantOutcome(**data)


# ============================================================================
# Learning Events
# ============================================================================

async def save_learning_event(event: LearningEvent) -> None:
    """Save a learning event."""
    ensure_data_dirs()
    path = f"{DATA_DIR}/learning_events/{event.id}.json"
    with open(path, 'w') as f:
        json.dump(event.model_dump(mode='json'), f, indent=2, default=str)


async def get_unprocessed_learning_events() -> List[LearningEvent]:
    """Get all unprocessed learning events."""
    ensure_data_dirs()
    events_dir = f"{DATA_DIR}/learning_events"
    events = []

    if not os.path.exists(events_dir):
        return events

    for filename in os.listdir(events_dir):
        if filename.endswith('.json'):
            path = os.path.join(events_dir, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                if not data.get('processed'):
                    events.append(LearningEvent(**data))

    return events


# ============================================================================
# Backwards Compatibility - Conversation Storage
# ============================================================================

def get_conversation_path(conversation_id: str) -> str:
    """Get the file path for a conversation."""
    return os.path.join(f"{DATA_DIR}/conversations", f"{conversation_id}.json")


def create_conversation(conversation_id: str) -> Dict[str, Any]:
    """Create a new conversation (backwards compatibility)."""
    ensure_data_dirs()

    conversation = {
        "id": conversation_id,
        "created_at": datetime.utcnow().isoformat(),
        "title": "New Application",
        "messages": []
    }

    path = get_conversation_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)

    return conversation


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """Load a conversation from storage."""
    path = get_conversation_path(conversation_id)
    if not os.path.exists(path):
        return None
    with open(path, 'r') as f:
        return json.load(f)


def save_conversation(conversation: Dict[str, Any]):
    """Save a conversation to storage."""
    ensure_data_dirs()
    path = get_conversation_path(conversation['id'])
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)


def list_conversations() -> List[Dict[str, Any]]:
    """List all conversations (metadata only)."""
    ensure_data_dirs()
    conv_dir = f"{DATA_DIR}/conversations"
    conversations = []

    if not os.path.exists(conv_dir):
        return conversations

    for filename in os.listdir(conv_dir):
        if filename.endswith('.json'):
            path = os.path.join(conv_dir, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                conversations.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "title": data.get("title", "New Application"),
                    "message_count": len(data["messages"])
                })

    conversations.sort(key=lambda x: x["created_at"], reverse=True)
    return conversations


def add_user_message(conversation_id: str, content: str):
    """Add a user message to a conversation."""
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "user",
        "content": content
    })

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    stage4: Optional[Dict[str, Any]] = None,
):
    """Add an assistant message with all stages to a conversation."""
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    message = {
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3,
    }

    if stage4:
        message["stage4"] = stage4

    conversation["messages"].append(message)
    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """Update the title of a conversation."""
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["title"] = title
    save_conversation(conversation)
