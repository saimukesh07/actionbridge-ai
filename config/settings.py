"""
ActionBridge AI - Application Settings & Configuration
Loads environment variables, manages path sandboxing, and exposes feature flags.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Base project directory
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file from project root
load_dotenv(BASE_DIR / ".env")

# Workspace Sandbox Directory for Controlled Execution
WORKSPACE_DIR = BASE_DIR / "workspace"
WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)

# Google Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
GEMINI_FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]

# Groq Configuration (Ultra-fast LLM inference)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
GROQ_FALLBACK_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

# Supabase Configuration (Optional for cloud authentication & storage)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()


def is_gemini_configured() -> bool:
    """Returns True if a real Gemini API key is provided."""
    return bool(GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your_"))


def is_groq_configured() -> bool:
    """Returns True if a real Groq API key is provided."""
    return bool(GROQ_API_KEY and not GROQ_API_KEY.startswith("your_") and not GROQ_API_KEY.startswith("gsk_placeholder"))


def is_ai_configured() -> bool:
    """Returns True if at least one live AI provider (Gemini or Groq) is ready."""
    return is_gemini_configured() or is_groq_configured()


def get_active_ai_provider() -> str:
    """Returns active provider: 'gemini', 'groq', or 'demo'."""
    if is_gemini_configured():
        return "gemini"
    elif is_groq_configured():
        return "groq"
    return "demo"


def is_supabase_configured() -> bool:
    """Returns True if both Supabase URL and Key are provided."""
    return bool(SUPABASE_URL and SUPABASE_KEY and not SUPABASE_KEY.startswith("your_"))

