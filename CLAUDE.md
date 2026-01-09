# CLAUDE.md - Technical Notes for Agentic Grants Council

This file contains technical details, architectural decisions, and important implementation notes for AI assistants working with this codebase.

## Quick Reference

```bash
# Start the system
./start.sh

# Or manually:
uv run python -m backend.main  # Backend on :8002
cd frontend && npm run dev     # Frontend on :5174

# Run tests
uv run pytest

# Install dependencies
uv sync                        # Python backend
cd frontend && npm install     # Node frontend
```

## Project Overview

The Agentic Grants Council is a 4-stage AI-powered grant application evaluation system. Four specialized AI agents evaluate applications from different perspectives, deliberate with each other, and vote on decisions. The system learns from outcomes over time.

### Key Features
- **4 Specialized Agents**: Technical, Ecosystem, Budget, and Impact reviewers
- **Persistent Agent Identities**: Agents accumulate observations and learn patterns
- **Team Matching**: Automatic identification of returning applicants
- **Deliberation**: Agents see each other's evaluations and can revise positions
- **Auto-execution**: High-confidence unanimous decisions can execute automatically
- **Learning Loops**: Feedback from overrides and outcomes improves agents
- **SSE Streaming**: Real-time progress updates during evaluation

## Architecture

### Project Structure

```
llm-grants-council-claude1/
├── backend/                    # Python FastAPI backend
│   ├── __init__.py
│   ├── config.py              # Configuration and thresholds
│   ├── openrouter.py          # OpenRouter API client
│   ├── models.py              # Pydantic data models
│   ├── agents.py              # Agent definitions and prompt building
│   ├── parser.py              # Application parsing with LLM
│   ├── storage.py             # Storage abstraction (JSON files)
│   ├── grants_council.py      # 4-stage orchestration
│   ├── learning.py            # Learning loops and observation management
│   ├── council.py             # Legacy 3-stage council (backwards compat)
│   └── main.py                # FastAPI application
├── frontend/                   # React Vite frontend
│   ├── src/
│   │   ├── App.jsx            # Router configuration
│   │   ├── api.js             # API client
│   │   ├── components/        # Reusable UI components
│   │   │   ├── Layout.jsx     # Main layout with navigation
│   │   │   ├── Sidebar.jsx    # Navigation sidebar
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── Stage1.jsx     # Evaluation stage displays
│   │   │   ├── Stage2.jsx
│   │   │   └── Stage3.jsx
│   │   └── pages/             # Route pages
│   │       ├── ApplicationsList.jsx
│   │       ├── ApplicationDetail.jsx
│   │       ├── SubmitApplication.jsx
│   │       ├── TeamsList.jsx
│   │       ├── ObservationsList.jsx
│   │       └── AgentsOverview.jsx
│   ├── package.json
│   └── vite.config.js
├── data/                       # JSON file storage (created at runtime)
├── pyproject.toml             # Python project config
├── start.sh                   # Development startup script
└── CLAUDE.md                  # This file
```

### Core Backend Modules

**`models.py`** - Pydantic Models (400 lines)
- `Application`: Grant application with raw and parsed content
- `ParsedApplication`: Structured application data with budget, milestones
- `TeamProfile`: Team history and reputation tracking
- `TeamMatch`: Team matching result with confidence
- `AgentCharacter`: Agent definition with prompts
- `AgentObservation`: Learned patterns
- `AgentEvaluation`: Agent's evaluation with score/recommendation
- `Deliberation`: Deliberation rounds
- `CouncilDecision`: Final decision with votes
- `GrantOutcome`: Post-funding outcome tracking
- `LearningEvent`: Events that trigger learning
- `Recommendation`: Enum (strong_approve → strong_reject)
- `ConfidenceLevel`: Enum (high, medium, low)
- `DecisionStatus`: Enum (pending, auto_approved, auto_rejected, needs_review, human_approved, human_rejected)

**`agents.py`** - Agent System (638 lines)
- `DEFAULT_AGENTS`: List of 4 agent definitions
- `build_evaluation_prompt()`: Assembles full context for evaluation
- `build_deliberation_prompt()`: Prompt for seeing others' evaluations
- `build_voting_prompt()`: Final voting prompt
- `parse_evaluation_response()`: Regex-based structured response parsing
- `parse_deliberation_response()`: Parses position changes
- `parse_vote_response()`: Parses final votes

**`grants_council.py`** - Main Orchestration (708 lines)
- `stage1_parse_and_contextualize()`: Parse + team matching
- `stage2_evaluate()`: Parallel agent evaluations
- `stage3_deliberate()`: Agents review each other's work
- `stage4_vote_and_decide()`: Aggregate votes and route
- `run_grants_council()`: Full synchronous flow
- `run_grants_council_streaming()`: Async generator with SSE events

**`storage.py`** - Data Persistence
- JSON file storage in `data/` directory
- Async functions for all CRUD operations
- Team matching with wallet, name, and member overlap
- Placeholder for vector similarity search

**`main.py`** - FastAPI Application (478 lines)
- CORS middleware configuration
- All API route handlers
- SSE streaming implementation
- Legacy conversation endpoints for backwards compatibility

### The 4-Stage Flow

```
1. PARSE & CONTEXTUALIZE
   └─> Parse application via LLM → Match team → Gather context
   └─> Creates Application record

2. EVALUATE (parallel)
   └─> Each agent evaluates independently
   └─> Considers: observations, team history, similar applications
   └─> Creates AgentEvaluation records

3. DELIBERATE
   └─> Agents see anonymized peer evaluations
   └─> Can revise positions with rationale
   └─> Creates Deliberation record

4. VOTE & DECIDE
   └─> Aggregate votes
   └─> Calculate consensus strength (0-1)
   └─> Route: auto-execute or human review
   └─> Creates CouncilDecision record
```

### Agent Roles

| Agent | Role | Focus | Model (Testing) |
|-------|------|-------|-----------------|
| Technical | Skeptical engineer | Feasibility, team capability, timeline realism | gemini-2.0-flash-exp:free |
| Ecosystem | Strategist | Program fit, ecosystem gaps, duplication | gemma-3-27b-it:free |
| Budget | Analyst | Amount reasonableness, structure, value | llama-3.1-405b-instruct:free |
| Impact | Assessor | Reach, lasting value, counterfactual | moonshotai/kimi-k2:free |

### Decision Routing Logic

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
- Split decisions (consensus < 60%)
- Large amounts (>= $50,000)
- Moderate consensus (60-85%)
```

## Frontend Architecture

### Tech Stack
- React 19.2 with React Router 7
- Vite 7 for bundling
- react-markdown for rendering
- CSS modules for styling

### Routes
| Path | Component | Description |
|------|-----------|-------------|
| `/` | ApplicationsList | List all applications |
| `/submit` | SubmitApplication | Submit new application |
| `/applications/:id` | ApplicationDetail | View full evaluation |
| `/teams` | TeamsList | List team profiles |
| `/teams/:id` | TeamsList | Team detail |
| `/observations` | ObservationsList | Manage agent observations |
| `/agents` | AgentsOverview | View agent configurations |

### API Client (`api.js`)
The frontend API client connects to `http://localhost:8002` and provides:
- `listApplications()`, `getApplication(id)`, `submitApplication()`
- `submitApplicationStream()` - SSE streaming for real-time updates
- `recordDecision()`, `recordOutcome()`
- `listTeams()`, `getTeam()`
- `listObservations()`, `approveObservation()`, `deprecateObservation()`
- `listAgents()`
- Legacy conversation API for backwards compatibility

## API Endpoints

### Application Endpoints
| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/applications` | List applications (optional: status, limit) |
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
| GET | `/api/observations` | List observations (optional: agent_id, status) |
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

### Environment Variables
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
API_PORT=8002
CORS_ORIGINS=http://localhost:5174,http://localhost:3000
```

### Port Configuration
**Note:** There's a discrepancy between config files:
- `backend/config.py`: Port 8002, CORS for 5174
- `start.sh`: References port 8001, 5173
- `frontend/src/api.js`: Connects to port 8002

When developing, ensure ports are consistent. The current config.py settings are:
- Backend: `http://localhost:8002`
- Frontend: `http://localhost:5174`

### Model Configuration (`config.py`)
```python
# Agent models (for production)
AGENT_MODELS = {
    "technical": "anthropic/claude-sonnet-4.5",
    "ecosystem": "openai/gpt-4o",
    "budget": "google/gemini-2.0-flash",
    "impact": "x-ai/grok-3-mini-beta",
}

# Utility models
PARSING_MODEL = "openai/gpt-4o-mini"
UTILITY_MODEL = "openai/gpt-4o-mini"

# Legacy council (for backwards compat)
COUNCIL_MODELS = [...]
CHAIRMAN_MODEL = "anthropic/claude-sonnet-4"
```

**Note:** `agents.py` currently overrides these with free-tier models for testing.

## Data Storage

### Directory Structure
```
data/
├── applications/      # Application records (JSON)
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
2. **Reviewed**: Has minimum evidence count (5 by default)
3. **Active**: Human-approved, used in evaluations
4. **Deprecated**: No longer used

## Learning System

### Override Learning
When a human overrides a council decision:
1. LearningEvent created with type="override"
2. Each agent can reflect on what they missed
3. Reflection may generate pattern observation
4. Observations start as drafts
5. Human reviews and approves useful patterns

### Outcome Learning
When a grant outcome is recorded:
1. LearningEvent created with type="outcome"
2. Each agent reflects on prediction accuracy
3. Did concerns materialize? Did strengths hold?
4. Generates observations about prediction patterns

### Observation Evidence
- Observations accumulate evidence from applications
- Confidence increases with validation ratio
- Observations with enough evidence get promoted
- Min evidence threshold: 5 (configurable)

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
- Fallback responses for failed agent queries

### Response Parsing
Agent responses are parsed with regex patterns:
- `SCORE: [1-10]`
- `RECOMMENDATION: [strong_approve/approve/lean_approve/lean_reject/reject/strong_reject]`
- `CONFIDENCE: [high/medium/low]`
- `RATIONALE:`, `STRENGTHS:`, `CONCERNS:`, `QUESTIONS:` sections

## Development Workflow

### Running the System
```bash
# Option 1: Use start script
./start.sh

# Option 2: Run manually
# Terminal 1:
uv run python -m backend.main

# Terminal 2:
cd frontend && npm run dev
```

### Important Implementation Details

**Relative Imports**: All backend modules use relative imports (e.g., `from .config import ...`). Always run as `python -m backend.main` from project root.

**Async Patterns**: Storage and API functions are async. Use `await` and `asyncio.gather()` for parallel operations.

**Pydantic Models**: All data models use Pydantic v2. Use `.model_dump()` for serialization, `.model_copy()` for cloning.

### Testing
```bash
# Run tests
uv run pytest

# Test with a sample application
curl -X POST http://localhost:8002/api/applications \
  -H "Content-Type: application/json" \
  -d '{"content": "Project: My Grant\nTeam: My Team\nAmount: $10,000\n..."}'

# Test streaming endpoint
curl -N http://localhost:8002/api/applications/stream \
  -H "Content-Type: application/json" \
  -d '{"content": "..."}'
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

## Dependencies

### Backend (Python 3.9+)
```
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
python-dotenv>=1.0.0
httpx>=0.27.0
pydantic>=2.9.0
```

Optional:
- `postgres`: sqlalchemy, asyncpg, alembic
- `vector`: openai, pinecone-client
- `dev`: pytest, pytest-asyncio, black, ruff

### Frontend (Node.js)
```
react: ^19.2.0
react-dom: ^19.2.0
react-markdown: ^10.1.0
react-router-dom: ^7.12.0
vite: ^7.2.4
```

## Future Enhancements

### Phase 1 (Current)
- [x] 4-stage council flow
- [x] Agent definitions with character prompts
- [x] JSON storage
- [x] Learning event generation
- [x] Multi-page React frontend
- [x] SSE streaming

### Phase 2 (Planned)
- [ ] PostgreSQL integration
- [ ] Vector database for similarity search
- [ ] Discord integration
- [ ] Webhook ingestion

### Phase 3 (Future)
- [ ] Batch learning analysis
- [ ] Cross-program learning
- [ ] Agent performance analytics
- [ ] Bootstrap from historical data (Crypto Grant Wire)

## Common Tasks

### Adding a New Agent
1. Add agent definition to `DEFAULT_AGENTS` in `agents.py`
2. Define: id, name, model, role, description, perspective, evaluation_focus
3. Write system_prompt and evaluation_instructions
4. Optionally update config.py AGENT_MODELS

### Modifying Decision Routing
Edit thresholds in `grants_council.py`:
- `AUTO_APPROVE_THRESHOLD`
- `AUTO_REJECT_THRESHOLD`
- `HUMAN_REVIEW_BUDGET_THRESHOLD`

### Adding New API Endpoints
1. Add route handler in `main.py`
2. Define request/response models in `models.py`
3. Implement storage functions in `storage.py`
4. Add client method in `frontend/src/api.js`

### Changing Models
Update model identifiers in `backend/config.py` or directly in `agents.py`. Models use OpenRouter format: `provider/model-name`.
