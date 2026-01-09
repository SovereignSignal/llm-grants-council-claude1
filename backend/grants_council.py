"""Grants Council orchestration - the 4-stage evaluation flow.

Stage 1: Parse & Contextualize - Parse application, match team, retrieve context
Stage 2: Evaluate - Each agent evaluates independently
Stage 3: Deliberate - Agents see each other's evaluations and can revise
Stage 4: Vote & Decide - Aggregate votes and route decision
"""

from typing import List, Dict, Any, Tuple, Optional
import asyncio
import uuid
from datetime import datetime

from .models import (
    Application,
    ParsedApplication,
    TeamProfile,
    TeamMatch,
    AgentEvaluation,
    AgentVote,
    CouncilDecision,
    Deliberation,
    DeliberationRound,
    DecisionStatus,
    Recommendation,
    ConfidenceLevel,
)
from .agents import (
    get_all_agents,
    build_evaluation_prompt,
    build_deliberation_prompt,
    parse_evaluation_response,
    parse_deliberation_response,
    AgentCharacter,
)
from .openrouter import query_model, query_models_parallel
from .parser import parse_application, validate_parsed_application
from .storage import (
    get_team_by_id,
    find_matching_team,
    get_relevant_observations,
    get_similar_applications,
    save_application,
    save_evaluation,
    save_deliberation,
    save_decision,
)


# ============================================================================
# Configuration
# ============================================================================

# Auto-execution thresholds
AUTO_APPROVE_THRESHOLD = 0.85  # Consensus strength for auto-approval
AUTO_REJECT_THRESHOLD = 0.85  # Consensus strength for auto-rejection
HUMAN_REVIEW_BUDGET_THRESHOLD = 50000  # Always require human review above this amount

# Deliberation settings
DELIBERATION_ROUNDS = 1  # Number of deliberation rounds


# ============================================================================
# Stage 1: Parse & Contextualize
# ============================================================================

async def stage1_parse_and_contextualize(
    raw_content: str,
    source: str = "manual",
    source_id: Optional[str] = None,
) -> Tuple[Application, Optional[ParsedApplication], Optional[TeamMatch]]:
    """
    Stage 1: Parse the application and gather context.

    1. Parse raw content into structured data
    2. Attempt to match team identity
    3. Return application object with context

    Args:
        raw_content: Raw application content
        source: Source of the application (webhook, api, manual)
        source_id: External ID from source system

    Returns:
        Tuple of (Application, ParsedApplication, TeamMatch)
    """
    # Create application record
    application = Application(
        id=str(uuid.uuid4()),
        created_at=datetime.utcnow(),
        source=source,
        source_id=source_id,
        raw_content=raw_content,
    )

    # Parse the application
    parsed = await parse_application(raw_content)

    if parsed:
        application.parsed = parsed

        # Validate
        validation = validate_parsed_application(parsed)
        if not validation['valid']:
            print(f"Application validation issues: {validation['issues']}")

        # Attempt team matching
        team_match = await find_matching_team(parsed)
        application.team_match = team_match
        if team_match and team_match.matched_team_id:
            application.matched_team_id = team_match.matched_team_id
    else:
        team_match = None
        print("Failed to parse application")

    # Save application
    await save_application(application)

    return application, parsed, team_match


# ============================================================================
# Stage 2: Evaluate
# ============================================================================

async def stage2_evaluate(
    application: Application,
    parsed: ParsedApplication,
    team_match: Optional[TeamMatch],
) -> List[AgentEvaluation]:
    """
    Stage 2: Each agent evaluates the application independently.

    1. For each agent, gather relevant observations and context
    2. Build evaluation prompt
    3. Query agent model
    4. Parse response into structured evaluation

    Args:
        application: The application object
        parsed: Parsed application data
        team_match: Team matching result

    Returns:
        List of AgentEvaluation objects
    """
    agents = get_all_agents()

    # Get team profile if matched
    team_profile = None
    if team_match and team_match.matched_team_id:
        team_profile = await get_team_by_id(team_match.matched_team_id)

    # Prepare evaluation tasks for each agent
    async def evaluate_with_agent(agent: AgentCharacter) -> AgentEvaluation:
        # Get relevant observations for this agent
        observations = await get_relevant_observations(
            agent_id=agent.id,
            tags=_extract_tags_from_application(parsed),
        )

        # Get similar applications
        similar_apps = await get_similar_applications(
            application_id=application.id,
            parsed=parsed,
            limit=3,
        )

        # Build prompt
        prompt = build_evaluation_prompt(
            agent=agent,
            application=parsed,
            team_profile=team_profile,
            similar_applications=similar_apps,
            relevant_observations=observations,
        )

        # Query the agent's model
        response = await query_model(
            model=agent.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=120.0,
        )

        # Parse response
        if response and response.get('content'):
            parsed_response = parse_evaluation_response(response['content'])
        else:
            # Fallback if model failed
            parsed_response = {
                "score": 5,
                "recommendation": Recommendation.LEAN_REJECT,
                "confidence": ConfidenceLevel.LOW,
                "rationale": "Error: Agent failed to respond",
                "strengths": [],
                "concerns": ["Agent did not provide evaluation"],
                "questions": [],
            }

        # Create evaluation object
        evaluation = AgentEvaluation(
            id=str(uuid.uuid4()),
            agent_id=agent.id,
            application_id=application.id,
            created_at=datetime.utcnow(),
            score=parsed_response["score"],
            recommendation=parsed_response["recommendation"],
            confidence=parsed_response["confidence"],
            rationale=parsed_response["rationale"],
            strengths=parsed_response["strengths"],
            concerns=parsed_response["concerns"],
            questions=parsed_response["questions"],
            observations_used=[o.id for o in observations],
            similar_applications_referenced=[a.get('id', '') for a in similar_apps],
        )

        # Save evaluation
        await save_evaluation(evaluation)

        return evaluation

    # Run evaluations in parallel
    evaluations = await asyncio.gather(*[
        evaluate_with_agent(agent) for agent in agents
    ])

    return list(evaluations)


def _extract_tags_from_application(parsed: ParsedApplication) -> List[str]:
    """Extract relevant tags from an application for observation retrieval."""
    tags = []

    if parsed.category:
        tags.append(parsed.category.lower())

    # Add amount ranges
    if parsed.requested_amount < 10000:
        tags.append("small_grant")
    elif parsed.requested_amount < 50000:
        tags.append("medium_grant")
    else:
        tags.append("large_grant")

    # Add team size indicators
    if len(parsed.team_members) == 1:
        tags.append("solo_founder")
    elif len(parsed.team_members) <= 3:
        tags.append("small_team")
    else:
        tags.append("larger_team")

    # Add milestone count
    if len(parsed.milestones) <= 2:
        tags.append("few_milestones")
    else:
        tags.append("detailed_milestones")

    return tags


# ============================================================================
# Stage 3: Deliberate
# ============================================================================

async def stage3_deliberate(
    application: Application,
    evaluations: List[AgentEvaluation],
) -> Tuple[Deliberation, List[AgentEvaluation]]:
    """
    Stage 3: Agents see each other's evaluations and can revise positions.

    1. Show each agent the anonymized evaluations from others
    2. Allow agents to update their positions
    3. Track position changes

    Args:
        application: The application object
        evaluations: List of initial evaluations

    Returns:
        Tuple of (Deliberation, updated evaluations)
    """
    agents = get_all_agents()
    agent_map = {a.id: a for a in agents}

    deliberation = Deliberation(
        application_id=application.id,
        rounds=[],
        created_at=datetime.utcnow(),
    )

    # Create summary of application
    parsed = application.parsed
    if parsed:
        app_summary = f"{parsed.project_name}: {parsed.project_summary}"
    else:
        app_summary = "Application details unavailable"

    # Deliberation round
    async def deliberate_for_agent(
        agent: AgentCharacter,
        own_eval: AgentEvaluation,
    ) -> Tuple[DeliberationRound, AgentEvaluation]:
        # Prepare other evaluations (anonymized)
        other_evals = []
        for e in evaluations:
            if e.agent_id != agent.id:
                other_evals.append({
                    "score": e.score,
                    "recommendation": e.recommendation.value,
                    "rationale": e.rationale,
                    "concerns": e.concerns,
                    "strengths": e.strengths,
                })

        # Build deliberation prompt
        prompt = build_deliberation_prompt(
            agent=agent,
            own_evaluation=own_eval,
            other_evaluations=other_evals,
            application_summary=app_summary,
        )

        # Query agent
        response = await query_model(
            model=agent.model,
            messages=[{"role": "user", "content": prompt}],
            timeout=90.0,
        )

        # Parse response
        if response and response.get('content'):
            parsed_delib = parse_deliberation_response(response['content'])
        else:
            parsed_delib = {
                "position_change": "maintained",
                "updated_recommendation": None,
                "response": "Agent did not respond",
            }

        # Create deliberation round
        round_record = DeliberationRound(
            round_number=1,
            agent_id=agent.id,
            other_evaluations_summary=f"Saw {len(other_evals)} other evaluations",
            response=parsed_delib["response"],
            position_change=parsed_delib["position_change"],
            updated_recommendation=parsed_delib.get("updated_recommendation"),
        )

        # Update evaluation if position changed
        updated_eval = own_eval.model_copy()
        if parsed_delib.get("updated_recommendation"):
            updated_eval.revised_recommendation = parsed_delib["updated_recommendation"]
            updated_eval.position_changed = True
            updated_eval.revision_rationale = parsed_delib["response"]

        return round_record, updated_eval

    # Run deliberation for all agents in parallel
    eval_map = {e.agent_id: e for e in evaluations}

    results = await asyncio.gather(*[
        deliberate_for_agent(agent_map[e.agent_id], e)
        for e in evaluations
        if e.agent_id in agent_map
    ])

    # Collect results
    updated_evaluations = []
    for round_record, updated_eval in results:
        deliberation.rounds.append(round_record)
        updated_evaluations.append(updated_eval)

    # Save deliberation
    await save_deliberation(deliberation)

    return deliberation, updated_evaluations


# ============================================================================
# Stage 4: Vote & Decide
# ============================================================================

async def stage4_vote_and_decide(
    application: Application,
    evaluations: List[AgentEvaluation],
    deliberation: Deliberation,
) -> CouncilDecision:
    """
    Stage 4: Aggregate votes and make/route decision.

    1. Collect final votes from all agents
    2. Calculate consensus
    3. Determine if auto-execute or route to human

    Args:
        application: The application object
        evaluations: Final evaluations after deliberation
        deliberation: Deliberation record

    Returns:
        CouncilDecision
    """
    # Collect votes
    votes = []
    for eval in evaluations:
        # Use revised recommendation if available
        final_rec = eval.revised_recommendation or eval.recommendation

        votes.append(AgentVote(
            agent_id=eval.agent_id,
            recommendation=final_rec,
            confidence=eval.confidence,
            rationale=eval.revision_rationale or eval.rationale,
        ))

    # Calculate consensus
    approve_votes = sum(1 for v in votes if v.recommendation in [
        Recommendation.STRONG_APPROVE,
        Recommendation.APPROVE,
        Recommendation.LEAN_APPROVE,
    ])
    reject_votes = sum(1 for v in votes if v.recommendation in [
        Recommendation.STRONG_REJECT,
        Recommendation.REJECT,
        Recommendation.LEAN_REJECT,
    ])

    total_votes = len(votes)
    unanimous = approve_votes == total_votes or reject_votes == total_votes

    # Calculate consensus strength (0-1 scale)
    if total_votes > 0:
        consensus_strength = max(approve_votes, reject_votes) / total_votes
    else:
        consensus_strength = 0

    # Determine primary recommendation
    if approve_votes > reject_votes:
        primary_rec = Recommendation.APPROVE
    elif reject_votes > approve_votes:
        primary_rec = Recommendation.REJECT
    else:
        # Tie - default to needs review
        primary_rec = Recommendation.LEAN_REJECT

    # Determine routing
    parsed = application.parsed
    requested_amount = parsed.requested_amount if parsed else 0

    auto_execute = False
    requires_human_review = True
    routing_reason = ""

    # Always require human review for large amounts
    if requested_amount >= HUMAN_REVIEW_BUDGET_THRESHOLD:
        routing_reason = f"Amount ${requested_amount:,.2f} exceeds auto-execution threshold"
    elif unanimous and consensus_strength >= AUTO_APPROVE_THRESHOLD and primary_rec == Recommendation.APPROVE:
        auto_execute = True
        requires_human_review = False
        routing_reason = "Unanimous high-confidence approval"
    elif unanimous and consensus_strength >= AUTO_REJECT_THRESHOLD and primary_rec == Recommendation.REJECT:
        auto_execute = True
        requires_human_review = False
        routing_reason = "Unanimous high-confidence rejection"
    elif consensus_strength < 0.6:
        routing_reason = "Split decision - requires human judgment"
    else:
        routing_reason = "Moderate consensus - recommend human review"

    # Generate summary
    summary = _generate_decision_summary(
        application, evaluations, votes, primary_rec, consensus_strength
    )

    # Collect key concerns and strengths
    all_concerns = []
    all_strengths = []
    for eval in evaluations:
        all_concerns.extend(eval.concerns[:2])  # Top 2 from each
        all_strengths.extend(eval.strengths[:2])

    # Deduplicate (simple approach)
    key_concerns = list(dict.fromkeys(all_concerns))[:5]
    key_strengths = list(dict.fromkeys(all_strengths))[:5]

    decision = CouncilDecision(
        application_id=application.id,
        created_at=datetime.utcnow(),
        votes=votes,
        unanimous=unanimous,
        consensus_strength=consensus_strength,
        primary_recommendation=primary_rec,
        auto_execute=auto_execute,
        requires_human_review=requires_human_review,
        routing_reason=routing_reason,
        summary=summary,
        key_concerns=key_concerns,
        key_strengths=key_strengths,
    )

    # Save decision
    await save_decision(decision)

    # Update application status
    if auto_execute:
        if primary_rec in [Recommendation.APPROVE, Recommendation.STRONG_APPROVE, Recommendation.LEAN_APPROVE]:
            application.status = DecisionStatus.AUTO_APPROVED
        else:
            application.status = DecisionStatus.AUTO_REJECTED
        application.final_decision = primary_rec.value
        application.decision_rationale = summary
        application.decided_at = datetime.utcnow()
        application.decided_by = "auto"
    else:
        application.status = DecisionStatus.NEEDS_REVIEW

    await save_application(application)

    return decision


def _generate_decision_summary(
    application: Application,
    evaluations: List[AgentEvaluation],
    votes: List[AgentVote],
    primary_rec: Recommendation,
    consensus_strength: float,
) -> str:
    """Generate a human-readable summary of the decision."""
    parsed = application.parsed
    project_name = parsed.project_name if parsed else "Unknown Project"
    amount = parsed.requested_amount if parsed else 0

    summary_parts = []

    # Header
    summary_parts.append(f"## Council Evaluation: {project_name}")
    summary_parts.append(f"\n**Requested Amount:** ${amount:,.2f}")
    summary_parts.append(f"\n**Recommendation:** {primary_rec.value.replace('_', ' ').title()}")
    summary_parts.append(f"\n**Consensus Strength:** {consensus_strength:.0%}")

    # Vote breakdown
    summary_parts.append("\n\n### Agent Votes")
    for vote in votes:
        summary_parts.append(f"\n- **{vote.agent_id.title()}**: {vote.recommendation.value.replace('_', ' ').title()} ({vote.confidence.value} confidence)")

    # Key points
    summary_parts.append("\n\n### Key Considerations")

    # Aggregate unique rationale points
    for eval in evaluations:
        summary_parts.append(f"\n**{eval.agent_id.title()} perspective:**")
        summary_parts.append(f"\n{eval.rationale[:300]}...")

    return "".join(summary_parts)


# ============================================================================
# Full Council Flow
# ============================================================================

async def run_grants_council(
    raw_content: str,
    source: str = "manual",
    source_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the complete grants council evaluation flow.

    Args:
        raw_content: Raw application content
        source: Source of application
        source_id: External source ID

    Returns:
        Dict with all stage results
    """
    result = {
        "application_id": None,
        "stage1": {"parsed": None, "team_match": None},
        "stage2": {"evaluations": []},
        "stage3": {"deliberation": None, "updated_evaluations": []},
        "stage4": {"decision": None},
        "status": None,
        "requires_human_review": True,
    }

    try:
        # Stage 1: Parse & Contextualize
        application, parsed, team_match = await stage1_parse_and_contextualize(
            raw_content, source, source_id
        )
        result["application_id"] = application.id
        result["stage1"]["parsed"] = parsed
        result["stage1"]["team_match"] = team_match

        if not parsed:
            result["status"] = "parse_failed"
            return result

        # Stage 2: Evaluate
        evaluations = await stage2_evaluate(application, parsed, team_match)
        result["stage2"]["evaluations"] = evaluations

        # Stage 3: Deliberate
        deliberation, updated_evals = await stage3_deliberate(application, evaluations)
        result["stage3"]["deliberation"] = deliberation
        result["stage3"]["updated_evaluations"] = updated_evals

        # Stage 4: Vote & Decide
        decision = await stage4_vote_and_decide(application, updated_evals, deliberation)
        result["stage4"]["decision"] = decision
        result["status"] = application.status.value
        result["requires_human_review"] = decision.requires_human_review

    except Exception as e:
        print(f"Error in grants council flow: {e}")
        result["status"] = "error"
        result["error"] = str(e)

    return result


# ============================================================================
# Streaming Version
# ============================================================================

async def run_grants_council_streaming(
    raw_content: str,
    source: str = "manual",
    source_id: Optional[str] = None,
):
    """
    Generator version of council flow that yields events as stages complete.

    Yields:
        Dict events with type and data
    """
    import json

    try:
        # Stage 1
        yield {"type": "stage1_start", "message": "Parsing application..."}

        application, parsed, team_match = await stage1_parse_and_contextualize(
            raw_content, source, source_id
        )

        yield {
            "type": "stage1_complete",
            "data": {
                "application_id": application.id,
                "parsed": parsed.model_dump() if parsed else None,
                "team_match": team_match.model_dump() if team_match else None,
            }
        }

        if not parsed:
            yield {"type": "error", "message": "Failed to parse application"}
            return

        # Stage 2
        yield {"type": "stage2_start", "message": "Agents evaluating..."}

        evaluations = await stage2_evaluate(application, parsed, team_match)

        yield {
            "type": "stage2_complete",
            "data": {
                "evaluations": [e.model_dump() for e in evaluations]
            }
        }

        # Stage 3
        yield {"type": "stage3_start", "message": "Agents deliberating..."}

        deliberation, updated_evals = await stage3_deliberate(application, evaluations)

        yield {
            "type": "stage3_complete",
            "data": {
                "deliberation": deliberation.model_dump(),
                "updated_evaluations": [e.model_dump() for e in updated_evals],
            }
        }

        # Stage 4
        yield {"type": "stage4_start", "message": "Voting and deciding..."}

        decision = await stage4_vote_and_decide(application, updated_evals, deliberation)

        yield {
            "type": "stage4_complete",
            "data": {
                "decision": decision.model_dump(),
                "status": application.status.value,
                "requires_human_review": decision.requires_human_review,
            }
        }

        yield {"type": "complete", "message": "Council evaluation complete"}

    except Exception as e:
        yield {"type": "error", "message": str(e)}
