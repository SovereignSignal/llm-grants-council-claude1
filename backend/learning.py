"""Learning system for the Grants Council.

Processes learning events (overrides, outcomes) to generate agent observations.
"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional

from .models import (
    AgentObservation,
    LearningEvent,
    Application,
    AgentEvaluation,
    GrantOutcome,
    ConfidenceLevel,
    ValidationStatus,
)
from .storage import (
    get_application,
    get_evaluations_for_application,
    get_outcome,
    get_unprocessed_learning_events,
    save_learning_event,
    save_observation,
    list_observations,
)
from .openrouter import query_model
from .config import MIN_OBSERVATION_EVIDENCE


# ============================================================================
# Learning Prompts
# ============================================================================

OVERRIDE_REFLECTION_PROMPT = """You are a grants council agent reflecting on a decision that was overridden by a human reviewer.

## Your Original Evaluation
Agent: {agent_id}
Score: {score}/10
Recommendation: {recommendation}
Rationale: {rationale}
Concerns: {concerns}
Strengths: {strengths}

## The Application
Project: {project_name}
Team: {team_name}
Amount: ${amount:,.2f}
Summary: {summary}

## What Happened
Your recommendation: {agent_recommendation}
Human decision: {human_decision}
Human rationale: {human_rationale}

## Your Task
Reflect on why the human reviewer made a different decision. Consider:
1. What signals did you miss that the human caught?
2. What factors might you have overweighted or underweighted?
3. Is there a pattern here that could inform future evaluations?

If you identify a useful pattern, format it as:

PATTERN: [One sentence describing the pattern]
CONTEXT: [When this pattern applies]
TAGS: [comma-separated tags like: small_grant, infrastructure, new_team, etc.]

If you don't see a clear pattern to learn from, just explain your reflection without the PATTERN format."""


OUTCOME_REFLECTION_PROMPT = """You are a grants council agent reflecting on the outcome of a grant you evaluated.

## Your Original Evaluation
Agent: {agent_id}
Score: {score}/10
Recommendation: {recommendation}
Rationale: {rationale}
Concerns: {concerns}
Strengths: {strengths}

## The Application
Project: {project_name}
Team: {team_name}
Amount: ${amount:,.2f}
Summary: {summary}

## Grant Outcome
Completed: {completed}
Completion: {completion_percentage}%
Quality Score: {quality_score}/10
Impact Assessment: {impact_assessment}
Issues: {issues}

## Your Task
Analyze whether your evaluation predicted the outcome well. Consider:
1. Did your concerns materialize or were they unfounded?
2. Did your identified strengths hold up?
3. What would you have evaluated differently knowing the outcome?
4. Is there a pattern here that could improve future evaluations?

If you identify a useful pattern, format it as:

PATTERN: [One sentence describing the pattern]
CONTEXT: [When this pattern applies]
TAGS: [comma-separated tags like: small_grant, infrastructure, new_team, etc.]

If you don't see a clear pattern to learn from, just explain your reflection without the PATTERN format."""


# ============================================================================
# Learning Event Processing
# ============================================================================

async def process_learning_events():
    """
    Process all unprocessed learning events.

    This should be run periodically (e.g., daily or on-demand).
    """
    events = await get_unprocessed_learning_events()

    for event in events:
        try:
            if event.event_type == "override":
                await process_override_event(event)
            elif event.event_type == "outcome":
                await process_outcome_event(event)

            # Mark as processed
            event.processed = True
            await save_learning_event(event)

        except Exception as e:
            print(f"Error processing learning event {event.id}: {e}")


async def process_override_event(event: LearningEvent):
    """Process a human override event to potentially generate observations."""
    if not event.application_id:
        return

    # Get application and evaluations
    application = await get_application(event.application_id)
    if not application or not application.parsed:
        return

    evaluations = await get_evaluations_for_application(event.application_id)
    if not evaluations:
        return

    parsed = application.parsed
    human_decision = event.context.get("new_decision", "unknown")
    human_rationale = event.context.get("rationale", "No rationale provided")

    # Have each agent reflect on the override
    for eval in evaluations:
        prompt = OVERRIDE_REFLECTION_PROMPT.format(
            agent_id=eval.agent_id,
            score=eval.score,
            recommendation=eval.recommendation.value,
            rationale=eval.rationale,
            concerns=", ".join(eval.concerns) if eval.concerns else "None noted",
            strengths=", ".join(eval.strengths) if eval.strengths else "None noted",
            project_name=parsed.project_name,
            team_name=parsed.team_name,
            amount=parsed.requested_amount,
            summary=parsed.project_summary,
            agent_recommendation=eval.recommendation.value,
            human_decision=human_decision,
            human_rationale=human_rationale,
        )

        response = await query_model(
            model="google/gemini-2.0-flash",
            messages=[{"role": "user", "content": prompt}],
            timeout=60.0,
        )

        if response and response.get("content"):
            observation = _parse_observation_from_response(
                response["content"],
                agent_id=eval.agent_id,
                application_id=event.application_id,
            )
            if observation:
                await save_observation(observation)
                event.generated_observations.append(observation.id)


async def process_outcome_event(event: LearningEvent):
    """Process a grant outcome event to potentially generate observations."""
    if not event.application_id:
        return

    # Get application, evaluations, and outcome
    application = await get_application(event.application_id)
    if not application or not application.parsed:
        return

    evaluations = await get_evaluations_for_application(event.application_id)
    outcome = await get_outcome(event.application_id)
    if not evaluations or not outcome:
        return

    parsed = application.parsed

    # Have each agent reflect on the outcome
    for eval in evaluations:
        prompt = OUTCOME_REFLECTION_PROMPT.format(
            agent_id=eval.agent_id,
            score=eval.score,
            recommendation=eval.recommendation.value,
            rationale=eval.rationale,
            concerns=", ".join(eval.concerns) if eval.concerns else "None noted",
            strengths=", ".join(eval.strengths) if eval.strengths else "None noted",
            project_name=parsed.project_name,
            team_name=parsed.team_name,
            amount=parsed.requested_amount,
            summary=parsed.project_summary,
            completed=outcome.completed,
            completion_percentage=outcome.completion_percentage,
            quality_score=outcome.quality_score or "N/A",
            impact_assessment=outcome.impact_assessment or "None provided",
            issues=", ".join(outcome.issues_encountered) if outcome.issues_encountered else "None noted",
        )

        response = await query_model(
            model="google/gemini-2.0-flash",
            messages=[{"role": "user", "content": prompt}],
            timeout=60.0,
        )

        if response and response.get("content"):
            observation = _parse_observation_from_response(
                response["content"],
                agent_id=eval.agent_id,
                application_id=event.application_id,
            )
            if observation:
                await save_observation(observation)
                event.generated_observations.append(observation.id)


def _parse_observation_from_response(
    response_text: str,
    agent_id: str,
    application_id: str,
) -> Optional[AgentObservation]:
    """Parse an observation from an agent's reflection response."""
    import re

    # Look for PATTERN: section
    pattern_match = re.search(r'PATTERN:\s*(.+?)(?=CONTEXT:|TAGS:|$)', response_text, re.DOTALL | re.IGNORECASE)
    if not pattern_match:
        return None

    pattern = pattern_match.group(1).strip()

    # Look for CONTEXT: section
    context = ""
    context_match = re.search(r'CONTEXT:\s*(.+?)(?=TAGS:|$)', response_text, re.DOTALL | re.IGNORECASE)
    if context_match:
        context = context_match.group(1).strip()

    # Look for TAGS: section
    tags = []
    tags_match = re.search(r'TAGS:\s*(.+?)$', response_text, re.DOTALL | re.IGNORECASE)
    if tags_match:
        tags_text = tags_match.group(1).strip()
        tags = [t.strip().lower().replace(" ", "_") for t in tags_text.split(",")]

    return AgentObservation(
        id=str(uuid.uuid4()),
        agent_id=agent_id,
        created_at=datetime.utcnow(),
        pattern=pattern,
        context=context,
        supporting_application_ids=[application_id],
        evidence_count=1,
        confidence=ConfidenceLevel.LOW,  # Start with low confidence
        tags=tags,
        status=ValidationStatus.DRAFT,  # Requires human review
    )


# ============================================================================
# Observation Management
# ============================================================================

async def consolidate_similar_observations(agent_id: str):
    """
    Consolidate similar observations for an agent.

    If multiple observations describe similar patterns, merge them
    and increase confidence.
    """
    observations = await list_observations(agent_id=agent_id)

    # Group by similar patterns (simple keyword overlap for now)
    # In production, use embeddings for semantic similarity

    # For now, just a placeholder
    # TODO: Implement actual consolidation logic
    pass


async def promote_observations_with_evidence():
    """
    Promote observations that have accumulated enough evidence.

    Observations with sufficient supporting cases and validations
    can be promoted from draft to reviewed or active.
    """
    observations = await list_observations(status="draft")

    for obs in observations:
        if obs.evidence_count >= MIN_OBSERVATION_EVIDENCE:
            # Move to reviewed status (still needs human approval for active)
            obs.status = ValidationStatus.REVIEWED
            await save_observation(obs)


async def update_observation_with_evidence(
    observation_id: str,
    application_id: str,
    validated: bool,
):
    """
    Update an observation with new evidence from an application.

    Args:
        observation_id: The observation to update
        application_id: The application providing evidence
        validated: Whether this application validates (True) or invalidates (False) the pattern
    """
    observations = await list_observations()
    observation = next((o for o in observations if o.id == observation_id), None)

    if observation is None:
        return

    if application_id not in observation.supporting_application_ids:
        observation.supporting_application_ids.append(application_id)
        observation.evidence_count = len(observation.supporting_application_ids)

    if validated:
        observation.validations += 1
    else:
        observation.invalidations += 1

    # Update confidence based on validation ratio
    total = observation.validations + observation.invalidations
    if total >= 3:
        ratio = observation.validations / total
        if ratio >= 0.8:
            observation.confidence = ConfidenceLevel.HIGH
        elif ratio >= 0.5:
            observation.confidence = ConfidenceLevel.MEDIUM
        else:
            observation.confidence = ConfidenceLevel.LOW

    observation.updated_at = datetime.utcnow()
    await save_observation(observation)


# ============================================================================
# Batch Learning
# ============================================================================

async def run_weekly_learning_batch():
    """
    Run weekly learning analysis.

    This performs deeper analysis across multiple applications
    to identify patterns that individual event processing might miss.
    """
    # TODO: Implement batch learning
    # 1. Analyze all applications from the past week
    # 2. Look for patterns in agent accuracy by category
    # 3. Identify systematic biases
    # 4. Generate high-level observations

    pass
