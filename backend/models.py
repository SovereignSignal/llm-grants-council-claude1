"""Pydantic models for the Agentic Grants Council."""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum


class DecisionStatus(str, Enum):
    """Status of a grant application decision."""
    PENDING = "pending"
    AUTO_APPROVED = "auto_approved"
    AUTO_REJECTED = "auto_rejected"
    NEEDS_REVIEW = "needs_review"
    HUMAN_APPROVED = "human_approved"
    HUMAN_REJECTED = "human_rejected"


class Recommendation(str, Enum):
    """Agent recommendation for an application."""
    STRONG_APPROVE = "strong_approve"
    APPROVE = "approve"
    LEAN_APPROVE = "lean_approve"
    LEAN_REJECT = "lean_reject"
    REJECT = "reject"
    STRONG_REJECT = "strong_reject"


class ConfidenceLevel(str, Enum):
    """Confidence level for agent evaluations."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ValidationStatus(str, Enum):
    """Status of an observation."""
    DRAFT = "draft"
    REVIEWED = "reviewed"
    ACTIVE = "active"
    DEPRECATED = "deprecated"


# ============================================================================
# Team Models
# ============================================================================

class TeamMember(BaseModel):
    """A member of a team."""
    name: str
    role: Optional[str] = None
    wallet_addresses: List[str] = Field(default_factory=list)
    aliases: List[str] = Field(default_factory=list)
    social_links: Dict[str, str] = Field(default_factory=dict)


class TeamProfile(BaseModel):
    """Profile of a team that has applied for grants."""
    id: str
    canonical_name: str
    aliases: List[str] = Field(default_factory=list)
    members: List[TeamMember] = Field(default_factory=list)
    wallet_addresses: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Track history
    application_ids: List[str] = Field(default_factory=list)
    grants_received: int = 0
    grants_completed: int = 0
    grants_failed: int = 0
    total_funding_received: float = 0.0

    # Reputation signals
    reputation_score: Optional[float] = None
    reputation_notes: Optional[str] = None


class TeamMatch(BaseModel):
    """Result of attempting to match a team from an application."""
    matched_team_id: Optional[str] = None
    match_confidence: float = 0.0
    match_type: str = "none"  # "exact_wallet", "fuzzy_name", "member_overlap", "none"
    requires_confirmation: bool = False
    match_evidence: List[str] = Field(default_factory=list)


# ============================================================================
# Application Models
# ============================================================================

class BudgetItem(BaseModel):
    """A line item in a budget."""
    category: str
    description: str
    amount: float
    justification: Optional[str] = None


class Milestone(BaseModel):
    """A project milestone."""
    title: str
    description: str
    deliverables: List[str] = Field(default_factory=list)
    timeline: Optional[str] = None
    funding_percentage: Optional[float] = None


class ParsedApplication(BaseModel):
    """Structured data parsed from a grant application."""
    # Basic info
    project_name: str
    project_summary: str
    project_description: str

    # Team info
    team_name: str
    team_members: List[TeamMember] = Field(default_factory=list)
    team_background: Optional[str] = None
    prior_work: Optional[str] = None
    wallet_address: Optional[str] = None

    # Funding
    requested_amount: float
    budget_breakdown: List[BudgetItem] = Field(default_factory=list)

    # Project details
    milestones: List[Milestone] = Field(default_factory=list)
    timeline: Optional[str] = None
    category: Optional[str] = None
    ecosystem_benefit: Optional[str] = None

    # Additional context
    github_url: Optional[str] = None
    website_url: Optional[str] = None
    social_links: Dict[str, str] = Field(default_factory=dict)
    additional_info: Optional[str] = None


class Application(BaseModel):
    """A grant application."""
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Source tracking
    source: str = "manual"  # "webhook", "api", "manual"
    source_id: Optional[str] = None

    # Raw and parsed content
    raw_content: str
    parsed: Optional[ParsedApplication] = None

    # Team matching
    team_match: Optional[TeamMatch] = None
    matched_team_id: Optional[str] = None

    # Decision status
    status: DecisionStatus = DecisionStatus.PENDING
    final_decision: Optional[str] = None
    decision_rationale: Optional[str] = None
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None  # "auto" or human reviewer ID

    # Human override tracking
    was_overridden: bool = False
    override_reason: Optional[str] = None


# ============================================================================
# Agent Models
# ============================================================================

class AgentCharacter(BaseModel):
    """Definition of an agent's character and perspective."""
    id: str
    name: str
    model: str  # OpenRouter model identifier
    role: str  # "technical", "ecosystem", "budget", "impact"

    # Character definition
    description: str
    perspective: str
    evaluation_focus: List[str] = Field(default_factory=list)

    # Prompt components
    system_prompt: str
    evaluation_instructions: str


class AgentObservation(BaseModel):
    """A learned pattern that an agent has developed."""
    id: str
    agent_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # The pattern
    pattern: str
    context: str

    # Evidence
    supporting_application_ids: List[str] = Field(default_factory=list)
    evidence_count: int = 0

    # Metadata
    confidence: ConfidenceLevel = ConfidenceLevel.MEDIUM
    tags: List[str] = Field(default_factory=list)
    status: ValidationStatus = ValidationStatus.DRAFT

    # Outcomes that validated/invalidated this observation
    validations: int = 0
    invalidations: int = 0


class AgentEvaluation(BaseModel):
    """An agent's evaluation of an application."""
    id: str
    agent_id: str
    application_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Initial evaluation
    score: int = Field(ge=1, le=10)
    recommendation: Recommendation
    confidence: ConfidenceLevel

    # Reasoning
    rationale: str
    strengths: List[str] = Field(default_factory=list)
    concerns: List[str] = Field(default_factory=list)
    questions: List[str] = Field(default_factory=list)

    # Context used
    observations_used: List[str] = Field(default_factory=list)
    similar_applications_referenced: List[str] = Field(default_factory=list)

    # Post-deliberation
    revised_score: Optional[int] = None
    revised_recommendation: Optional[Recommendation] = None
    revision_rationale: Optional[str] = None
    position_changed: bool = False


# ============================================================================
# Deliberation Models
# ============================================================================

class DeliberationRound(BaseModel):
    """A round of deliberation between agents."""
    round_number: int
    agent_id: str

    # What this agent sees
    other_evaluations_summary: str

    # Response
    response: str
    position_change: Optional[str] = None  # "maintained", "strengthened", "weakened", "reversed"
    updated_recommendation: Optional[Recommendation] = None


class Deliberation(BaseModel):
    """The full deliberation process for an application."""
    application_id: str
    rounds: List[DeliberationRound] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# Voting and Decision Models
# ============================================================================

class AgentVote(BaseModel):
    """An agent's final vote on an application."""
    agent_id: str
    recommendation: Recommendation
    confidence: ConfidenceLevel
    rationale: str


class CouncilDecision(BaseModel):
    """The council's collective decision on an application."""
    application_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Individual votes
    votes: List[AgentVote] = Field(default_factory=list)

    # Aggregated result
    unanimous: bool = False
    consensus_strength: float = 0.0  # 0-1 scale
    primary_recommendation: Recommendation

    # Decision routing
    auto_execute: bool = False
    requires_human_review: bool = True
    routing_reason: str

    # Generated summary
    summary: str
    key_concerns: List[str] = Field(default_factory=list)
    key_strengths: List[str] = Field(default_factory=list)


# ============================================================================
# Outcome and Learning Models
# ============================================================================

class MilestoneOutcome(BaseModel):
    """Outcome of a milestone."""
    milestone_index: int
    completed: bool
    completion_date: Optional[datetime] = None
    notes: Optional[str] = None


class GrantOutcome(BaseModel):
    """Final outcome of a funded grant."""
    application_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Status
    completed: bool
    completion_percentage: float = 0.0

    # Milestone tracking
    milestone_outcomes: List[MilestoneOutcome] = Field(default_factory=list)

    # Assessment
    impact_assessment: Optional[str] = None
    quality_score: Optional[int] = None

    # Notes
    notes: Optional[str] = None
    issues_encountered: List[str] = Field(default_factory=list)


class LearningEvent(BaseModel):
    """An event that triggers agent learning."""
    id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

    event_type: str  # "override", "outcome", "batch_review"
    application_id: Optional[str] = None
    agent_id: Optional[str] = None

    # What happened
    description: str
    context: Dict[str, Any] = Field(default_factory=dict)

    # What was learned (if any)
    generated_observations: List[str] = Field(default_factory=list)

    processed: bool = False


# ============================================================================
# API Request/Response Models
# ============================================================================

class SubmitApplicationRequest(BaseModel):
    """Request to submit a new application."""
    content: str
    source: str = "api"
    source_id: Optional[str] = None


class EvaluationResponse(BaseModel):
    """Response containing full evaluation results."""
    application_id: str
    parsed_application: Optional[ParsedApplication] = None
    team_match: Optional[TeamMatch] = None

    # Stage results
    evaluations: List[AgentEvaluation] = Field(default_factory=list)
    deliberation: Optional[Deliberation] = None
    decision: Optional[CouncilDecision] = None

    # Status
    status: DecisionStatus
    requires_human_review: bool


class HumanDecisionRequest(BaseModel):
    """Request for a human to make a decision."""
    decision: str  # "approve" or "reject"
    rationale: str
    override_council: bool = False


class RecordOutcomeRequest(BaseModel):
    """Request to record grant outcome."""
    completed: bool
    completion_percentage: float = 0.0
    milestone_outcomes: List[MilestoneOutcome] = Field(default_factory=list)
    impact_assessment: Optional[str] = None
    quality_score: Optional[int] = None
    notes: Optional[str] = None
