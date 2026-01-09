# CLAUDE.md - Technical Notes for Agentic Grants Council

This file contains technical details, architectural decisions, and important implementation notes for the Agentic Grants Council system.

## Project Overview

The Agentic Grants Council is a 4-stage AI-powered grant application evaluation system. Four specialized AI agents evaluate applications from different perspectives, deliberate with each other, and vote on decisions. The system learns from outcomes over time.

### Key Features
- **4 Specialized Agents**: Technical, Ecosystem, Budget, and Impact reviewers
- **Persistent Agent Identities**: Agents accumulate observations and learn patterns
- **Team Matching**: Automatic identification of returning applicants
- **Deliberation**: Agents see each other's evaluations and can revise positions
- **Auto-execution**: High-confidence unanimous decisions can execute automatically
- **Learning Loops**: Feedback from overrides and outcomes improves agents

## Architecture

### Backend Structure (`backend/`)

```
backend/
├── __init__.py
├── config.py          # Configuration and thresholds
├── openrouter.py      # OpenRouter API client
├── models.py          # Pydantic data models
├── agents.py          # Agent definitions and prompt building
├── parser.py          # Application parsing with LLM
├── storage.py         # Storage abstraction (JSON files)
├── grants_council.py  # 4-stage orchestration
├── learning.py        # Learning loops and observation management
├── council.py         # Legacy 3-stage council (backwards compat)
└── main.py            # FastAPI application
```

### Core Modules

**`models.py`** - Pydantic Models
- `Application`: Grant application with raw and parsed content
- `ParsedApplication`: Structured application data
- `TeamProfile`: Team history and reputation
- `TeamMatch`: Team matching result
- `AgentCharacter`: Agent definition with prompts
- `AgentObservation`: Learned patterns
- `AgentEvaluation`: Agent's evaluation of application
- `Deliberation`: Deliberation rounds
- `CouncilDecision`: Final decision with votes
- `GrantOutcome`: Post-funding outcome
- `LearningEvent`: Events that trigger learning

**`agents.py`** - Agent System
- 4 default agents: Technical, Ecosystem, Budget, Impact
- Each has character prompt, evaluation instructions, model assignment
- `build_evaluation_prompt()`: Assembles full context for evaluation
- `build_deliberation_prompt()`: Prompt for seeing others' evaluations
- Response parsing: Extracts structured data from LLM responses

**`parser.py`** - Application Parsing
- `parse_application()`: LLM-powered parsing of freeform text
- Extracts: team, budget, milestones, timeline, etc.
- `validate_parsed_application()`: Checks completeness

**`grants_council.py`** - Main Orchestration
- `stage1_parse_and_contextualize()`: Parse + team matching
- `stage2_evaluate()`: Parallel agent evaluations
- `stage3_deliberate()`: Agents review each other's work
- `stage4_vote_and_decide()`: Aggregate votes and route

**`storage.py`** - Data Persistence
- JSON file storage for development
- Async functions for all operations
- Team matching with wallet, name, and member overlap
- Placeholder for vector similarity search

**`learning.py`** - Learning System
- Process override events (human disagreed with council)
- Process outcome events (grant succeeded/failed)
- Generate observations from reflections
- Observation consolidation and promotion

### The 4-Stage Flow

```
1. PARSE & CONTEXTUALIZE
   └─> Parse application → Match team → Gather context

2. EVALUATE (parallel)
   └─> Each agent evaluates independently
   └─> Considers: observations, team history, similar applications

3. DELIBERATE
   └─> Agents see anonymized peer evaluations
   └─> Can revise positions with rationale

4. VOTE & DECIDE
   └─> Aggregate votes
   └─> Calculate consensus
   └─> Route: auto-execute or human review
```

### Agent Roles

| Agent | Role | Focus |
|-------|------|-------|
| Technical | Skeptical engineer | Feasibility, team capability, timeline realism |
| Ecosystem | Strategist | Program fit, ecosystem gaps, duplication |
| Budget | Analyst | Amount reasonableness, structure, value |
| Impact | Assessor | Reach, lasting value, counterfactual |

### Decision Routing

```python
# Auto-approve conditions:
- Unanimous approval votes
- Consensus strength >= 85%
- Amount < $50,000

# Auto-reject conditions:
- Unanimous rejection votes
- Consensus strength >= 85%
- Amount < $50,000

# Human review:
- Split decisions
- Large amounts (>= $50,000)
- Low confidence
```

## API Endpoints

### Application Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/applications` | List applications |
| POST | `/api/applications` | Submit new application |
| POST | `/api/applications/stream` | Submit with SSE streaming |
| GET | `/api/applications/{id}` | Get full evaluation |
| POST | `/api/applications/{id}/decision` | Record human decision |
| POST | `/api/applications/{id}/outcome` | Record grant outcome |

### Team Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/teams` | List team profiles |
| GET | `/api/teams/{id}` | Get team details |

### Observation Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/observations` | List observations |
| POST | `/api/observations/{id}/approve` | Approve draft observation |
| DELETE | `/api/observations/{id}` | Deprecate observation |

### Info Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| GET | `/api/agents` | List council agents |

### Legacy Endpoints (backwards compatibility)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/conversations` | List conversations |
| POST | `/api/conversations` | Create conversation |
| POST | `/api/conversations/{id}/message` | Send message |
| POST | `/api/conversations/{id}/message/stream` | Streaming message |

## Configuration

Key environment variables:
```bash
# Required
OPENROUTER_API_KEY=your_key_here

# Optional with defaults
DATA_DIR=data
AUTO_APPROVE_THRESHOLD=0.85
AUTO_REJECT_THRESHOLD=0.85
HUMAN_REVIEW_BUDGET_THRESHOLD=50000
DELIBERATION_ROUNDS=1
MIN_OBSERVATION_EVIDENCE=5
API_HOST=0.0.0.0
API_PORT=8001
CORS_ORIGINS=http://localhost:5173,http://localhost:3000
```

## Data Storage

### Directory Structure
```
data/
├── applications/      # Application records
├── teams/            # Team profiles
├── evaluations/      # Agent evaluations
├── deliberations/    # Deliberation records
├── decisions/        # Council decisions
├── observations/     # Learned patterns
├── outcomes/         # Grant outcomes
├── learning_events/  # Events for learning
└── conversations/    # Legacy conversation storage
```

### Observation Lifecycle
1. **Draft**: Generated from learning events
2. **Reviewed**: Has minimum evidence count
3. **Active**: Human-approved, used in evaluations
4. **Deprecated**: No longer used

## Learning System

### Override Learning
When a human overrides a council decision:
1. Each agent reflects on what they missed
2. Reflection may generate pattern observation
3. Observations start as drafts
4. Human reviews and approves useful patterns

### Outcome Learning
When a grant outcome is recorded:
1. Each agent reflects on prediction accuracy
2. Did concerns materialize? Did strengths hold?
3. Generates observations about prediction patterns

### Observation Evidence
- Observations accumulate evidence from applications
- Confidence increases with validation ratio
- Observations with enough evidence get promoted

## Key Design Decisions

### Agent Anonymization in Deliberation
- Agents see other evaluations without agent IDs
- Prevents favoritism or dismissiveness based on source
- Focuses deliberation on the arguments themselves

### Observation Gating
- All observations start as drafts
- Minimum evidence threshold before promotion
- Human approval required for activation
- Prevents bad patterns from propagating

### Team Matching Strategy
1. Exact wallet match (definitive)
2. Fuzzy name match (high confidence)
3. Member overlap (medium confidence)
4. Ambiguous matches require confirmation

### Graceful Degradation
- If one agent fails, continue with others
- If parsing fails, evaluation can't proceed
- Errors logged but don't crash the system

## Running the System

```bash
# Start backend
uv run python -m backend.main

# Or use the startup script
./start.sh
```

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`). Run as `python -m backend.main` from project root.

### Port Configuration
- Backend: 8001
- Frontend: 5173 (Vite default)

## Future Enhancements

### Phase 1 (Current)
- [x] 4-stage council flow
- [x] Agent definitions with character prompts
- [x] JSON storage
- [x] Learning event generation

### Phase 2 (Planned)
- [ ] PostgreSQL integration
- [ ] Vector database for similarity search
- [ ] Discord integration
- [ ] Updated frontend for grants

### Phase 3 (Future)
- [ ] Batch learning analysis
- [ ] Cross-program learning
- [ ] Agent performance analytics
- [ ] Bootstrap from historical data (Crypto Grant Wire)

## Testing

```bash
# Run tests
uv run pytest

# Test with a sample application
curl -X POST http://localhost:8001/api/applications \
  -H "Content-Type: application/json" \
  -d '{"content": "Project: My Grant\nTeam: My Team\nAmount: $10,000\n..."}'
```

## Module Dependencies

```
config.py ──────────────────────────────────────────────┐
    ↓                                                   │
openrouter.py ──────────────────────────────────────────┤
    ↓                                                   │
models.py ──────────────────────────────────────────────┤
    ↓                                                   │
agents.py (uses models, openrouter) ────────────────────┤
    ↓                                                   │
parser.py (uses models, openrouter) ────────────────────┤
    ↓                                                   │
storage.py (uses models, config) ───────────────────────┤
    ↓                                                   │
grants_council.py (uses all above) ─────────────────────┤
    ↓                                                   │
learning.py (uses models, storage, openrouter) ─────────┤
    ↓                                                   │
main.py (uses all above) ───────────────────────────────┘
```
