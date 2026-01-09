"""Configuration for the Agentic Grants Council."""

import os
from dotenv import load_dotenv

load_dotenv()

# OpenRouter API key
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# Data directory for storage
DATA_DIR = os.getenv("DATA_DIR", "data")

# ============================================================================
# Agent Configuration
# ============================================================================

# Default models for each agent role
AGENT_MODELS = {
    "technical": "anthropic/claude-sonnet-4.5",
    "ecosystem": "openai/gpt-4o",
    "budget": "google/gemini-2.0-flash",
    "impact": "x-ai/grok-3-mini-beta",
}

# Model for parsing applications
PARSING_MODEL = "openai/gpt-4o-mini"

# Model for generating titles/summaries
UTILITY_MODEL = "openai/gpt-4o-mini"

# ============================================================================
# Council Decision Thresholds
# ============================================================================

# Auto-execution thresholds (0-1 scale)
AUTO_APPROVE_THRESHOLD = float(os.getenv("AUTO_APPROVE_THRESHOLD", "0.85"))
AUTO_REJECT_THRESHOLD = float(os.getenv("AUTO_REJECT_THRESHOLD", "0.85"))

# Budget threshold - always require human review above this amount
HUMAN_REVIEW_BUDGET_THRESHOLD = float(os.getenv("HUMAN_REVIEW_BUDGET_THRESHOLD", "50000"))

# Deliberation settings
DELIBERATION_ROUNDS = int(os.getenv("DELIBERATION_ROUNDS", "1"))

# ============================================================================
# Learning Configuration
# ============================================================================

# Minimum evidence count before an observation can become active
MIN_OBSERVATION_EVIDENCE = int(os.getenv("MIN_OBSERVATION_EVIDENCE", "5"))

# ============================================================================
# API Configuration
# ============================================================================

# Server settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8002"))

# CORS origins
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5174,http://localhost:3000").split(",")

# ============================================================================
# Legacy Configuration (for backwards compatibility)
# ============================================================================

# Council members - kept for backwards compatibility with original LLM Council
COUNCIL_MODELS = [
    "openai/gpt-4o",
    "google/gemini-2.0-flash",
    "anthropic/claude-sonnet-4.5",
    "x-ai/grok-3-mini-beta",
]

# Chairman model - synthesizes final response (legacy)
CHAIRMAN_MODEL = "anthropic/claude-sonnet-4"
