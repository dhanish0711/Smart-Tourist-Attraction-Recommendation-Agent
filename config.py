"""
Configuration and settings for Smart Tourist Attraction Recommendation Agent.
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent

class Settings(BaseSettings):
    APP_NAME: str = "Smart Tourist Attraction Recommendation Agent"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = True
    BASE_DIR: Path = BASE_DIR
    
    # Free LLM API Keys
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    
    # Web Intelligence API (Tavily free tier)
    TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")
    
    # Langflow API
    LANGFLOW_API_URL: str = os.getenv("LANGFLOW_API_URL", "http://127.0.0.1:7860/api/v1/run")
    LANGFLOW_FLOW_ID: str = os.getenv("LANGFLOW_FLOW_ID", "")
    LANGFLOW_API_KEY: str = os.getenv("LANGFLOW_API_KEY", "")
    
    # File Paths
    DATA_DIR: Path = BASE_DIR / "data"
    SKILLS_DIR: Path = BASE_DIR / "data" / "skills_library"
    OUTPUT_DIR: Path = BASE_DIR / "output"
    
    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", 8000))

    # n8n Integration — Public tunnel URL (localtunnel / ngrok)
    # Set this in .env: N8N_TUNNEL_URL=https://your-tunnel.loca.lt
    N8N_TUNNEL_URL: str = os.getenv("N8N_TUNNEL_URL", "")

    # n8n Cloud Webhook URL (for triggering cloud workflows)
    N8N_WEBHOOK_URL: str = os.getenv("N8N_WEBHOOK_URL", "https://dhanish0711.app.n8n.cloud/webhook/trip-monitor")

    # Public base URL used in email links and webhook responses
    # Checks RENDER_EXTERNAL_URL, RENDER_EXTERNAL_HOSTNAME, then N8N_TUNNEL_URL, then localhost fallback
    @property
    def PUBLIC_BASE_URL(self) -> str:
        render_url = os.getenv("RENDER_EXTERNAL_URL", "") or os.getenv("RENDER_EXTERNAL_HOSTNAME", "")
        if render_url:
            if not render_url.startswith("http"):
                render_url = f"https://{render_url}"
            return render_url.rstrip("/")
        if os.getenv("RENDER"):
            return "https://smart-tourist-attraction-recommendation.onrender.com"
        if self.N8N_TUNNEL_URL:
            return self.N8N_TUNNEL_URL.rstrip("/")
        return f"http://127.0.0.1:{self.PORT}"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

# Ensure directories exist
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
settings.SKILLS_DIR.mkdir(parents=True, exist_ok=True)
settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
