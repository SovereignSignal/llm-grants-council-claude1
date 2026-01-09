"""Application parsing for the Grants Council.

Parses freeform grant applications into structured data.
"""

from typing import Optional, Dict, Any, List
from .models import (
    ParsedApplication,
    TeamMember,
    BudgetItem,
    Milestone,
)
from .openrouter import query_model
from .config import PARSING_MODEL


PARSING_PROMPT = """You are a grant application parser. Your task is to extract structured information from a grant application.

Given the following grant application, extract and structure the information.

## Application Content:
{application_content}

---

Parse this application and respond with the following JSON structure. If a field is not present or unclear, use null.

```json
{{
  "project_name": "string - the project/proposal name",
  "project_summary": "string - a brief 2-3 sentence summary",
  "project_description": "string - the full project description",
  "team_name": "string - the team or organization name",
  "team_members": [
    {{
      "name": "string",
      "role": "string or null",
      "wallet_addresses": ["string"] or [],
      "aliases": ["string"] or [],
      "social_links": {{"twitter": "url", "github": "url"}} or {{}}
    }}
  ],
  "team_background": "string or null - team experience and history",
  "prior_work": "string or null - relevant prior work",
  "wallet_address": "string or null - primary wallet for receiving funds",
  "requested_amount": number - the amount requested in USD (or convert to USD),
  "budget_breakdown": [
    {{
      "category": "string - e.g., Development, Design, Marketing",
      "description": "string",
      "amount": number,
      "justification": "string or null"
    }}
  ],
  "milestones": [
    {{
      "title": "string",
      "description": "string",
      "deliverables": ["string"],
      "timeline": "string or null - e.g., '4 weeks'",
      "funding_percentage": number or null - percentage of total funding
    }}
  ],
  "timeline": "string or null - overall project timeline",
  "category": "string or null - e.g., Infrastructure, DeFi, NFT, Tooling, Education",
  "ecosystem_benefit": "string or null - how this benefits the ecosystem",
  "github_url": "string or null",
  "website_url": "string or null",
  "social_links": {{"twitter": "url", "discord": "url"}} or {{}},
  "additional_info": "string or null - any other relevant information"
}}
```

Respond ONLY with the JSON object, no additional text or markdown code blocks."""


async def parse_application(raw_content: str) -> Optional[ParsedApplication]:
    """
    Parse a raw application into structured data using an LLM.

    Args:
        raw_content: The raw application content (freeform text)

    Returns:
        ParsedApplication if successful, None if parsing failed
    """
    import json

    prompt = PARSING_PROMPT.format(application_content=raw_content)

    response = await query_model(
        model=PARSING_MODEL,
        messages=[{"role": "user", "content": prompt}],
        timeout=60.0
    )

    if response is None:
        return None

    content = response.get('content', '')

    # Clean up the response (remove markdown code blocks if present)
    content = content.strip()
    if content.startswith('```json'):
        content = content[7:]
    if content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    content = content.strip()

    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        # Try to extract JSON from the response
        import re
        json_match = re.search(r'\{[\s\S]*\}', content)
        if json_match:
            try:
                data = json.loads(json_match.group())
            except json.JSONDecodeError:
                return None
        else:
            return None

    # Convert to ParsedApplication
    try:
        team_members = []
        for member_data in data.get('team_members', []):
            if member_data and isinstance(member_data, dict):
                # Filter out None values from social_links
                raw_social = member_data.get('social_links', {}) or {}
                social_links = {k: v for k, v in raw_social.items() if v is not None}
                team_members.append(TeamMember(
                    name=member_data.get('name', 'Unknown'),
                    role=member_data.get('role'),
                    wallet_addresses=member_data.get('wallet_addresses', []) or [],
                    aliases=member_data.get('aliases', []) or [],
                    social_links=social_links,
                ))

        budget_items = []
        for item_data in data.get('budget_breakdown', []):
            if item_data and isinstance(item_data, dict):
                budget_items.append(BudgetItem(
                    category=item_data.get('category', 'Other'),
                    description=item_data.get('description', ''),
                    amount=float(item_data.get('amount', 0)),
                    justification=item_data.get('justification'),
                ))

        milestones = []
        for ms_data in data.get('milestones', []):
            if ms_data and isinstance(ms_data, dict):
                milestones.append(Milestone(
                    title=ms_data.get('title', 'Milestone'),
                    description=ms_data.get('description', ''),
                    deliverables=ms_data.get('deliverables', []),
                    timeline=ms_data.get('timeline'),
                    funding_percentage=ms_data.get('funding_percentage'),
                ))

        return ParsedApplication(
            project_name=data.get('project_name', 'Unknown Project'),
            project_summary=data.get('project_summary', ''),
            project_description=data.get('project_description', ''),
            team_name=data.get('team_name', 'Unknown Team'),
            team_members=team_members,
            team_background=data.get('team_background'),
            prior_work=data.get('prior_work'),
            wallet_address=data.get('wallet_address'),
            requested_amount=float(data.get('requested_amount', 0)),
            budget_breakdown=budget_items,
            milestones=milestones,
            timeline=data.get('timeline'),
            category=data.get('category'),
            ecosystem_benefit=data.get('ecosystem_benefit'),
            github_url=data.get('github_url'),
            website_url=data.get('website_url'),
            social_links={k: v for k, v in (data.get('social_links', {}) or {}).items() if v is not None},
            additional_info=data.get('additional_info'),
        )

    except Exception as e:
        import traceback
        print(f"Error converting parsed data to model: {e}")
        traceback.print_exc()
        return None


def validate_parsed_application(parsed: ParsedApplication) -> Dict[str, Any]:
    """
    Validate a parsed application and return issues.

    Returns:
        Dict with 'valid' bool and 'issues' list
    """
    issues = []

    if not parsed.project_name or parsed.project_name == 'Unknown Project':
        issues.append("Missing project name")

    if not parsed.project_description:
        issues.append("Missing project description")

    if not parsed.team_name or parsed.team_name == 'Unknown Team':
        issues.append("Missing team name")

    if parsed.requested_amount <= 0:
        issues.append("Invalid or missing requested amount")

    if not parsed.milestones:
        issues.append("No milestones defined")

    if not parsed.budget_breakdown:
        issues.append("No budget breakdown provided")

    # Check budget adds up to requested amount
    if parsed.budget_breakdown:
        total_budget = sum(item.amount for item in parsed.budget_breakdown)
        if abs(total_budget - parsed.requested_amount) > 1:  # Allow $1 rounding error
            issues.append(f"Budget breakdown (${total_budget:,.2f}) doesn't match requested amount (${parsed.requested_amount:,.2f})")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
    }


async def extract_key_info_for_matching(raw_content: str) -> Dict[str, Any]:
    """
    Extract key identifying information for team matching.

    This is a lighter-weight extraction focused on matching identities
    rather than full application parsing.
    """
    prompt = f"""Extract identifying information from this grant application for team matching.

Application:
{raw_content[:3000]}

Respond with JSON:
```json
{{
  "team_name": "string",
  "member_names": ["string"],
  "wallet_addresses": ["string"],
  "github_usernames": ["string"],
  "twitter_handles": ["string"],
  "email_addresses": ["string"],
  "previous_grant_mentions": ["string - any mentions of previous grants or applications"]
}}
```

Only include information that is explicitly stated. Use empty arrays if not found."""

    response = await query_model(
        model=PARSING_MODEL,
        messages=[{"role": "user", "content": prompt}],
        timeout=30.0
    )

    if response is None:
        return {
            "team_name": None,
            "member_names": [],
            "wallet_addresses": [],
            "github_usernames": [],
            "twitter_handles": [],
            "email_addresses": [],
            "previous_grant_mentions": [],
        }

    content = response.get('content', '')

    # Clean up
    content = content.strip()
    if content.startswith('```json'):
        content = content[7:]
    if content.startswith('```'):
        content = content[3:]
    if content.endswith('```'):
        content = content[:-3]
    content = content.strip()

    try:
        import json
        return json.loads(content)
    except json.JSONDecodeError:
        return {
            "team_name": None,
            "member_names": [],
            "wallet_addresses": [],
            "github_usernames": [],
            "twitter_handles": [],
            "email_addresses": [],
            "previous_grant_mentions": [],
        }
