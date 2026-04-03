"""Configuration from environment variables."""
import os
from dotenv import load_dotenv

# Load from .env if present, otherwise rely on shell env
load_dotenv(os.path.expanduser("~/alpha-engine/.env"))
load_dotenv()  # Also check local .env

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
XAI_API_KEY = os.environ.get("XAI_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

# Model defaults
# DeepSeek R1 = "deepseek-reasoner" (thinking, best for structured output)
# DeepSeek V3 = "deepseek-chat" (fast, cheap, no chain-of-thought)
DEFAULT_MODEL = "deepseek-reasoner"
FALLBACK_MODEL = "deepseek-chat"

# Output directory
OUTPUT_DIR = os.path.expanduser("~/content-engine/output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
