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

# Supabase Configuration (Optional for cloud authentication & storage)
SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "").strip()


def is_gemini_configured() -> bool:
    """Returns True if a real Gemini API key is provided (not empty or default placeholder)."""
    return bool(GEMINI_API_KEY and not GEMINI_API_KEY.startswith("your_"))


def is_supabase_configured() -> bool:
    """Returns True if both Supabase URL and Key are provided."""
    return bool(SUPABASE_URL and SUPABASE_KEY and not SUPABASE_KEY.startswith("your_"))
