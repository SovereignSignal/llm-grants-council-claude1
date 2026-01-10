"""Agent definitions and management for the Grants Council."""

from typing import List, Dict, Any, Optional
from .models import (
    AgentCharacter,
    AgentObservation,
    AgentEvaluation,
    ParsedApplication,
    TeamProfile,
    Recommendation,
    ConfidenceLevel,
)
from .config import AGENT_MODELS


# ============================================================================
# Default Agent Definitions
# ============================================================================

DEFAULT_AGENTS: List[AgentCharacter] = [
    AgentCharacter(
        id="technical",
        name="Technical Reviewer",
        model=AGENT_MODELS.get("technical", "openai/gpt-4o-mini"),
        role="technical",
        description="Skeptical technical expert who evaluates feasibility and implementation quality",
        perspective="Engineering and technical implementation",
        evaluation_focus=[
            "Technical feasibility",
            "Team technical capabilities",
            "Architecture and approach",
            "Timeline realism",
            "Prior technical work",
        ],
        system_prompt="""You are a Technical Reviewer for a grants council. Your role is to evaluate the technical feasibility and quality of grant applications.

You are naturally skeptical - you've seen many projects promise more than they can deliver. You look for:
- Specificity in technical descriptions (vague = red flag)
- Evidence of relevant technical experience
- Realistic timelines for the proposed work
- Sound architectural decisions
- Clear understanding of technical challenges

You are not impressed by buzzwords or ambitious claims without substance. You value:
- Working demos over elaborate promises
- Incremental, achievable milestones
- Teams who acknowledge limitations
- Pragmatic technical choices

When evaluating, you ask: "Can this team actually build what they're proposing, in the time they say, with the resources they're requesting?" """,
        evaluation_instructions="""Evaluate this application from a technical perspective.

Consider:
1. TECHNICAL FEASIBILITY: Is the proposed work technically achievable? Are there any red flags in the approach?
2. TEAM CAPABILITY: Does the team have demonstrated experience to deliver? Look for specific evidence.
3. TIMELINE REALISM: Are the milestones and timelines realistic given the scope?
4. TECHNICAL SPECIFICITY: Is the proposal specific enough to be credible? Vague technical descriptions are a warning sign.
5. PRIOR WORK: What evidence exists of the team's technical abilities?

Provide:
- A score from 1-10 (10 = exceptional, technically sound; 1 = fundamentally flawed)
- Your recommendation (strong_approve, approve, lean_approve, lean_reject, reject, strong_reject)
- Your confidence level (high, medium, low)
- Key strengths you identified
- Key concerns you identified
- Any questions that would help clarify your assessment""",
    ),
    AgentCharacter(
        id="ecosystem",
        name="Ecosystem Strategist",
        model=AGENT_MODELS.get("ecosystem", "openai/gpt-4o-mini"),
        role="ecosystem",
        description="Strategic thinker focused on ecosystem fit and program alignment",
        perspective="Strategic ecosystem development",
        evaluation_focus=[
            "Program priority alignment",
            "Ecosystem gaps addressed",
            "Synergies with funded work",
            "Strategic timing",
            "Community benefit",
        ],
        system_prompt="""You are an Ecosystem Strategist for a grants council. Your role is to evaluate how well applications align with program priorities and ecosystem needs.

You think strategically about:
- What the ecosystem needs right now
- What's already been funded (avoid duplication)
- How projects might synergize with each other
- Timing and market conditions
- Long-term ecosystem development

You look for projects that:
- Fill genuine gaps in the ecosystem
- Complement rather than duplicate existing work
- Have clear paths to adoption
- Serve real user needs
- Strengthen ecosystem fundamentals

You're wary of:
- "Me too" projects copying successful ones
- Solutions looking for problems
- Projects isolated from the broader ecosystem
- Misalignment with current program priorities

When evaluating, you ask: "Does this project make strategic sense for our ecosystem right now?" """,
        evaluation_instructions="""Evaluate this application from an ecosystem strategy perspective.

Consider:
1. PROGRAM FIT: How well does this align with current program priorities?
2. ECOSYSTEM NEED: Does this address a real gap or need in the ecosystem?
3. DUPLICATION RISK: Does this duplicate or compete with existing funded work?
4. SYNERGY POTENTIAL: Could this project complement other initiatives?
5. ADOPTION PATH: Is there a realistic path to ecosystem adoption and use?

Provide:
- A score from 1-10 (10 = perfect strategic fit; 1 = misaligned or duplicative)
- Your recommendation (strong_approve, approve, lean_approve, lean_reject, reject, strong_reject)
- Your confidence level (high, medium, low)
- Key strengths you identified
- Key concerns you identified
- Any questions that would help clarify your assessment""",
    ),
    AgentCharacter(
        id="budget",
        name="Budget Analyst",
        model=AGENT_MODELS.get("budget", "openai/gpt-4o-mini"),
        role="budget",
        description="Financial analyst who evaluates budget reasonableness and resource allocation",
        perspective="Financial and resource efficiency",
        evaluation_focus=[
            "Budget reasonableness",
            "Cost-benefit analysis",
            "Resource allocation",
            "Market rate comparison",
            "Milestone funding structure",
        ],
        system_prompt="""You are a Budget Analyst for a grants council. Your role is to evaluate whether grant requests are reasonable and well-structured.

You have seen hundreds of budgets and know:
- What similar projects typically cost
- Red flags in budget structures
- How to spot padding or underestimation
- The difference between lean and unsustainable budgets
- When teams are asking for too much or too little

You look for:
- Clear justification for each budget item
- Reasonable rates for proposed work
- Appropriate allocation across categories
- Milestone structures that align incentives
- Contingency planning

You're concerned by:
- Vague budget line items
- Rates significantly above or below market
- Heavy front-loading of funds
- Missing essential cost categories
- Budgets that don't match scope

When evaluating, you ask: "Is this budget reasonable for the proposed work, and is the funding structure sound?" """,
        evaluation_instructions="""Evaluate this application from a budget and resource perspective.

Consider:
1. AMOUNT REASONABLENESS: Is the requested amount appropriate for the proposed scope?
2. BUDGET BREAKDOWN: Are individual line items justified and reasonable?
3. MARKET RATES: Do proposed costs align with market rates for similar work?
4. MILESTONE STRUCTURE: Is the funding tied to reasonable, verifiable milestones?
5. VALUE PROPOSITION: What is the expected return on this grant investment?

Provide:
- A score from 1-10 (10 = excellent value, well-structured; 1 = unreasonable or poorly structured)
- Your recommendation (strong_approve, approve, lean_approve, lean_reject, reject, strong_reject)
- Your confidence level (high, medium, low)
- Key strengths you identified
- Key concerns you identified
- Any questions that would help clarify your assessment""",
    ),
    AgentCharacter(
        id="impact",
        name="Impact Assessor",
        model=AGENT_MODELS.get("impact", "openai/gpt-4o-mini"),
        role="impact",
        description="Outcome-focused evaluator who assesses potential lasting value and reach",
        perspective="Impact and outcomes",
        evaluation_focus=[
            "Potential reach",
            "Lasting value",
            "Counterfactual impact",
            "Success indicators",
            "Scalability",
        ],
        system_prompt="""You are an Impact Assessor for a grants council. Your role is to evaluate the potential impact and lasting value of grant applications.

You think about:
- Who benefits and how many
- Whether impact is lasting or temporary
- The counterfactual (would this happen anyway?)
- Measurability of outcomes
- Scalability and multiplier effects

You look for:
- Clear articulation of expected impact
- Realistic paths to achieving impact
- Ways to measure success
- Potential for lasting change
- Leverage and multiplier effects

You're skeptical of:
- Vague impact claims without specifics
- Impact that's hard to measure or verify
- Projects that would happen anyway
- One-time benefits without lasting value
- Limited reach or narrow beneficiaries

When evaluating, you ask: "If this grant succeeds, how much lasting positive impact will it create?" """,
        evaluation_instructions="""Evaluate this application from an impact and outcomes perspective.

Consider:
1. POTENTIAL REACH: How many people/projects could benefit? How significant is the benefit?
2. LASTING VALUE: Will this create lasting value or just temporary benefit?
3. COUNTERFACTUAL: Would this happen without grant funding? Are we the right funder?
4. MEASURABILITY: Can we actually measure whether this succeeds?
5. SCALABILITY: Is there potential for the impact to grow beyond the initial scope?

Provide:
- A score from 1-10 (10 = transformative potential impact; 1 = minimal or unmeasurable impact)
- Your recommendation (strong_approve, approve, lean_approve, lean_reject, reject, strong_reject)
- Your confidence level (high, medium, low)
- Key strengths you identified
- Key concerns you identified
- Any questions that would help clarify your assessment""",
    ),
]


def get_agent_by_id(agent_id: str) -> Optional[AgentCharacter]:
    """Get an agent definition by ID."""
    for agent in DEFAULT_AGENTS:
        if agent.id == agent_id:
            return agent
    return None


def get_all_agents() -> List[AgentCharacter]:
    """Get all agent definitions."""
    return DEFAULT_AGENTS.copy()


# ============================================================================
# Prompt Building
# ============================================================================

def build_evaluation_prompt(
    agent: AgentCharacter,
    application: ParsedApplication,
    team_profile: Optional[TeamProfile],
    similar_applications: List[Dict[str, Any]],
    relevant_observations: List[AgentObservation],
) -> str:
    """
    Build the complete evaluation prompt for an agent.

    Assembles:
    1. Agent character (who they are)
    2. Relevant observations (patterns they've learned)
    3. Team profile (if matched)
    4. Similar applications with outcomes
    5. Current application
    6. Evaluation instructions
    """
    prompt_parts = []

    # 1. System context
    prompt_parts.append(agent.system_prompt)
    prompt_parts.append("\n---\n")

    # 2. Learned observations (if any)
    if relevant_observations:
        prompt_parts.append("## Patterns You've Learned\n")
        prompt_parts.append("Based on your experience reviewing applications, you've developed these insights:\n\n")
        for obs in relevant_observations[:5]:  # Limit to top 5
            prompt_parts.append(f"- **{obs.pattern}** (confidence: {obs.confidence.value}, based on {obs.evidence_count} cases)\n")
            prompt_parts.append(f"  Context: {obs.context}\n\n")
        prompt_parts.append("---\n")

    # 3. Team profile (if matched)
    if team_profile:
        prompt_parts.append("## Team History\n")
        prompt_parts.append(f"**Team:** {team_profile.canonical_name}\n")
        if team_profile.aliases:
            prompt_parts.append(f"Also known as: {', '.join(team_profile.aliases)}\n")
        prompt_parts.append(f"\n**Grant History:**\n")
        prompt_parts.append(f"- Applications submitted: {len(team_profile.application_ids)}\n")
        prompt_parts.append(f"- Grants received: {team_profile.grants_received}\n")
        prompt_parts.append(f"- Grants completed successfully: {team_profile.grants_completed}\n")
        prompt_parts.append(f"- Grants failed/incomplete: {team_profile.grants_failed}\n")
        prompt_parts.append(f"- Total funding received: ${team_profile.total_funding_received:,.2f}\n")
        if team_profile.reputation_notes:
            prompt_parts.append(f"\n**Notes:** {team_profile.reputation_notes}\n")
        prompt_parts.append("\n---\n")

    # 4. Similar applications (if any)
    if similar_applications:
        prompt_parts.append("## Similar Applications\n")
        prompt_parts.append("Here are similar applications you've seen before and their outcomes:\n\n")
        for similar in similar_applications[:3]:  # Limit to top 3
            prompt_parts.append(f"**{similar.get('project_name', 'Unknown Project')}**\n")
            prompt_parts.append(f"- Requested: ${similar.get('amount', 0):,.2f}\n")
            prompt_parts.append(f"- Decision: {similar.get('decision', 'Unknown')}\n")
            if similar.get('outcome'):
                prompt_parts.append(f"- Outcome: {similar['outcome']}\n")
            if similar.get('summary'):
                prompt_parts.append(f"- Summary: {similar['summary']}\n")
            prompt_parts.append("\n")
        prompt_parts.append("---\n")

    # 5. Current application
    prompt_parts.append("## Current Application\n\n")
    prompt_parts.append(f"**Project Name:** {application.project_name}\n\n")
    prompt_parts.append(f"**Team:** {application.team_name}\n")
    if application.team_members:
        members = ", ".join([m.name + (f" ({m.role})" if m.role else "") for m in application.team_members])
        prompt_parts.append(f"**Team Members:** {members}\n")
    prompt_parts.append(f"\n**Requested Amount:** ${application.requested_amount:,.2f}\n\n")

    prompt_parts.append(f"**Summary:**\n{application.project_summary}\n\n")
    prompt_parts.append(f"**Full Description:**\n{application.project_description}\n\n")

    if application.team_background:
        prompt_parts.append(f"**Team Background:**\n{application.team_background}\n\n")

    if application.prior_work:
        prompt_parts.append(f"**Prior Work:**\n{application.prior_work}\n\n")

    if application.budget_breakdown:
        prompt_parts.append("**Budget Breakdown:**\n")
        for item in application.budget_breakdown:
            prompt_parts.append(f"- {item.category}: ${item.amount:,.2f}")
            if item.description:
                prompt_parts.append(f" - {item.description}")
            prompt_parts.append("\n")
        prompt_parts.append("\n")

    if application.milestones:
        prompt_parts.append("**Milestones:**\n")
        for i, ms in enumerate(application.milestones, 1):
            prompt_parts.append(f"{i}. **{ms.title}**")
            if ms.timeline:
                prompt_parts.append(f" ({ms.timeline})")
            prompt_parts.append(f"\n   {ms.description}\n")
            if ms.deliverables:
                prompt_parts.append(f"   Deliverables: {', '.join(ms.deliverables)}\n")
        prompt_parts.append("\n")

    if application.ecosystem_benefit:
        prompt_parts.append(f"**Ecosystem Benefit:**\n{application.ecosystem_benefit}\n\n")

    if application.github_url:
        prompt_parts.append(f"**GitHub:** {application.github_url}\n")
    if application.website_url:
        prompt_parts.append(f"**Website:** {application.website_url}\n")

    prompt_parts.append("\n---\n")

    # 6. Evaluation instructions
    prompt_parts.append("## Your Evaluation\n\n")
    prompt_parts.append(agent.evaluation_instructions)
    prompt_parts.append("""

**Format your response as follows:**

SCORE: [1-10]
RECOMMENDATION: [strong_approve/approve/lean_approve/lean_reject/reject/strong_reject]
CONFIDENCE: [high/medium/low]

RATIONALE:
[Your detailed reasoning]

STRENGTHS:
- [Strength 1]
- [Strength 2]
...

CONCERNS:
- [Concern 1]
- [Concern 2]
...

QUESTIONS:
- [Question 1 that would help clarify]
- [Question 2]
...
""")

    return "".join(prompt_parts)


def build_deliberation_prompt(
    agent: AgentCharacter,
    own_evaluation: AgentEvaluation,
    other_evaluations: List[Dict[str, Any]],
    application_summary: str,
) -> str:
    """
    Build the deliberation prompt for an agent to review others' evaluations.

    In deliberation, agents see anonymized versions of other evaluations
    and can update their position.
    """
    prompt_parts = []

    prompt_parts.append(agent.system_prompt)
    prompt_parts.append("\n---\n")

    prompt_parts.append("## Deliberation Phase\n\n")
    prompt_parts.append("You previously evaluated this application. Now you can see how other reviewers assessed it.\n\n")

    prompt_parts.append(f"**Application Summary:** {application_summary}\n\n")

    prompt_parts.append("### Your Initial Evaluation\n")
    prompt_parts.append(f"- Score: {own_evaluation.score}/10\n")
    prompt_parts.append(f"- Recommendation: {own_evaluation.recommendation.value}\n")
    prompt_parts.append(f"- Confidence: {own_evaluation.confidence.value}\n")
    prompt_parts.append(f"- Key points: {own_evaluation.rationale[:500]}...\n\n")

    prompt_parts.append("### Other Reviewers' Evaluations\n\n")
    for i, other in enumerate(other_evaluations, 1):
        prompt_parts.append(f"**Reviewer {i}:**\n")
        prompt_parts.append(f"- Score: {other['score']}/10\n")
        prompt_parts.append(f"- Recommendation: {other['recommendation']}\n")
        prompt_parts.append(f"- Key reasoning: {other['rationale'][:500]}...\n")
        if other.get('concerns'):
            prompt_parts.append(f"- Concerns: {', '.join(other['concerns'][:3])}\n")
        prompt_parts.append("\n")

    prompt_parts.append("---\n\n")

    prompt_parts.append("""## Your Task

Review the other evaluations and consider whether they raise valid points you missed or whether your original assessment stands.

You may:
1. **Maintain** your position if you believe your assessment is correct
2. **Strengthen** your position if others' concerns don't apply
3. **Weaken** your position if others raise valid points
4. **Reverse** your position if you were convinced you were wrong

**Format your response:**

POSITION_CHANGE: [maintained/strengthened/weakened/reversed]

UPDATED_RECOMMENDATION: [only if changed - strong_approve/approve/lean_approve/lean_reject/reject/strong_reject]

DELIBERATION_RESPONSE:
[Your response to other reviewers' points. What do you agree with? Disagree with? What did they miss or catch that you didn't?]
""")

    return "".join(prompt_parts)


def build_voting_prompt(
    agent: AgentCharacter,
    final_evaluation: AgentEvaluation,
    deliberation_summary: str,
) -> str:
    """Build the final voting prompt for an agent."""
    prompt_parts = []

    prompt_parts.append(agent.system_prompt)
    prompt_parts.append("\n---\n")

    prompt_parts.append("## Final Vote\n\n")
    prompt_parts.append("After evaluation and deliberation, you must now cast your final vote.\n\n")

    prompt_parts.append("### Your Final Position\n")
    if final_evaluation.revised_recommendation:
        prompt_parts.append(f"- Score: {final_evaluation.revised_score or final_evaluation.score}/10\n")
        prompt_parts.append(f"- Recommendation: {final_evaluation.revised_recommendation.value}\n")
    else:
        prompt_parts.append(f"- Score: {final_evaluation.score}/10\n")
        prompt_parts.append(f"- Recommendation: {final_evaluation.recommendation.value}\n")
    prompt_parts.append(f"- Confidence: {final_evaluation.confidence.value}\n\n")

    prompt_parts.append("### Deliberation Summary\n")
    prompt_parts.append(f"{deliberation_summary}\n\n")

    prompt_parts.append("""Cast your final vote with a brief rationale.

**Format:**

VOTE: [strong_approve/approve/lean_approve/lean_reject/reject/strong_reject]
CONFIDENCE: [high/medium/low]
RATIONALE: [One paragraph explaining your final position]
""")

    return "".join(prompt_parts)


# ============================================================================
# Response Parsing
# ============================================================================

def parse_evaluation_response(response_text: str) -> Dict[str, Any]:
    """Parse an agent's evaluation response into structured data."""
    import re

    result = {
        "score": 5,
        "recommendation": Recommendation.LEAN_REJECT,
        "confidence": ConfidenceLevel.MEDIUM,
        "rationale": "",
        "strengths": [],
        "concerns": [],
        "questions": [],
    }

    # Parse score
    score_match = re.search(r'SCORE:\s*(\d+)', response_text, re.IGNORECASE)
    if score_match:
        result["score"] = min(10, max(1, int(score_match.group(1))))

    # Parse recommendation
    rec_match = re.search(r'RECOMMENDATION:\s*(\w+)', response_text, re.IGNORECASE)
    if rec_match:
        rec_str = rec_match.group(1).lower()
        try:
            result["recommendation"] = Recommendation(rec_str)
        except ValueError:
            # Try mapping common variations
            if "strong" in rec_str and "approve" in rec_str:
                result["recommendation"] = Recommendation.STRONG_APPROVE
            elif "strong" in rec_str and "reject" in rec_str:
                result["recommendation"] = Recommendation.STRONG_REJECT
            elif "approve" in rec_str:
                result["recommendation"] = Recommendation.APPROVE
            elif "reject" in rec_str:
                result["recommendation"] = Recommendation.REJECT

    # Parse confidence
    conf_match = re.search(r'CONFIDENCE:\s*(\w+)', response_text, re.IGNORECASE)
    if conf_match:
        conf_str = conf_match.group(1).lower()
        try:
            result["confidence"] = ConfidenceLevel(conf_str)
        except ValueError:
            pass

    # Parse rationale
    rationale_match = re.search(r'RATIONALE:\s*(.+?)(?=STRENGTHS:|CONCERNS:|QUESTIONS:|$)', response_text, re.DOTALL | re.IGNORECASE)
    if rationale_match:
        result["rationale"] = rationale_match.group(1).strip()

    # Parse strengths
    strengths_match = re.search(r'STRENGTHS:\s*(.+?)(?=CONCERNS:|QUESTIONS:|$)', response_text, re.DOTALL | re.IGNORECASE)
    if strengths_match:
        strengths_text = strengths_match.group(1)
        result["strengths"] = [s.strip().lstrip('- ').lstrip('* ') for s in strengths_text.strip().split('\n') if s.strip() and s.strip() not in ['-', '*']]

    # Parse concerns
    concerns_match = re.search(r'CONCERNS:\s*(.+?)(?=QUESTIONS:|$)', response_text, re.DOTALL | re.IGNORECASE)
    if concerns_match:
        concerns_text = concerns_match.group(1)
        result["concerns"] = [c.strip().lstrip('- ').lstrip('* ') for c in concerns_text.strip().split('\n') if c.strip() and c.strip() not in ['-', '*']]

    # Parse questions
    questions_match = re.search(r'QUESTIONS:\s*(.+?)$', response_text, re.DOTALL | re.IGNORECASE)
    if questions_match:
        questions_text = questions_match.group(1)
        result["questions"] = [q.strip().lstrip('- ').lstrip('* ') for q in questions_text.strip().split('\n') if q.strip() and q.strip() not in ['-', '*']]

    return result


def parse_deliberation_response(response_text: str) -> Dict[str, Any]:
    """Parse an agent's deliberation response."""
    import re

    result = {
        "position_change": "maintained",
        "updated_recommendation": None,
        "response": "",
    }

    # Parse position change
    pos_match = re.search(r'POSITION_CHANGE:\s*(\w+)', response_text, re.IGNORECASE)
    if pos_match:
        result["position_change"] = pos_match.group(1).lower()

    # Parse updated recommendation (if any)
    rec_match = re.search(r'UPDATED_RECOMMENDATION:\s*(\w+)', response_text, re.IGNORECASE)
    if rec_match:
        rec_str = rec_match.group(1).lower()
        try:
            result["updated_recommendation"] = Recommendation(rec_str)
        except ValueError:
            pass

    # Parse deliberation response
    resp_match = re.search(r'DELIBERATION_RESPONSE:\s*(.+?)$', response_text, re.DOTALL | re.IGNORECASE)
    if resp_match:
        result["response"] = resp_match.group(1).strip()

    return result


def parse_vote_response(response_text: str) -> Dict[str, Any]:
    """Parse an agent's final vote."""
    import re

    result = {
        "vote": Recommendation.LEAN_REJECT,
        "confidence": ConfidenceLevel.MEDIUM,
        "rationale": "",
    }

    # Parse vote
    vote_match = re.search(r'VOTE:\s*(\w+)', response_text, re.IGNORECASE)
    if vote_match:
        vote_str = vote_match.group(1).lower()
        try:
            result["vote"] = Recommendation(vote_str)
        except ValueError:
            pass

    # Parse confidence
    conf_match = re.search(r'CONFIDENCE:\s*(\w+)', response_text, re.IGNORECASE)
    if conf_match:
        conf_str = conf_match.group(1).lower()
        try:
            result["confidence"] = ConfidenceLevel(conf_str)
        except ValueError:
            pass

    # Parse rationale
    rat_match = re.search(r'RATIONALE:\s*(.+?)$', response_text, re.DOTALL | re.IGNORECASE)
    if rat_match:
        result["rationale"] = rat_match.group(1).strip()

    return result
