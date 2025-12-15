"""Application configuration"""
from pydantic_settings import BaseSettings
from pydantic import field_validator
from functools import lru_cache
from typing import List
from urllib.parse import urlparse


class Settings(BaseSettings):
    """Application settings"""
    
    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/llm_audit"
    
    # LLM Provider
    # - openai: https://api.openai.com/v1 with OpenAI keys (sk-...)
    # - openrouter: https://openrouter.ai/api/v1 with OpenRouter keys (sk-or-...)
    llm_provider: str = "openai"
    
    # OpenAI / OpenRouter (shared via OpenAI SDK client)
    openai_api_key: str
    openai_model: str = "gpt-4o"
    # Force explicit API base; default is OpenAI's official endpoint.
    # (Helps avoid accidental OpenRouter usage / misconfiguration.)
    openai_base_url: str = "https://api.openai.com/v1"
    
    # OpenRouter-specific optional metadata headers
    # (Recommended by OpenRouter for attribution; safe to leave empty.)
    openrouter_referer: str = ""
    openrouter_title: str = "LLM Audit Engine"
    
    # Scraping limits
    max_pages_target: int = 60
    max_pages_competitor: int = 15
    request_timeout: int = 10
    max_page_size_mb: int = 5
    total_scraping_timeout: int = 300  # 5 minutes
    
    # Paths & Storage
    reports_dir: str = "./reports"
    reports_retention_days: int = 30  # Cleanup old reports after N days

    # Exports (URL-first product)
    # PDF export is optional and MUST NOT block audits. Default: disabled.
    enable_pdf_export: bool = False

    # Legacy exports (URL-first product does NOT design for HTML/PDF)
    # Keep only for optional export/debug later; default disabled.
    enable_html_export: bool = False
    
    # Server
    backend_url: str = "http://localhost:8000"
    frontend_url: str = "http://localhost:3000"
    
    # CORS - for production, set specific origins
    cors_origins: str = "http://localhost:3000,http://localhost:5173"  # Comma-separated
    
    # Environment
    environment: str = "development"  # development, production
    
    # Stripe Configuration
    stripe_api_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_audit_price_id: str = ""  # Price ID for $199 one-time audit
    stripe_starter_price_id: str = ""
    stripe_growth_price_id: str = ""
    stripe_scale_price_id: str = ""
    
    # JWT Configuration for magic link authentication
    jwt_secret_key: str = "change-this-to-a-random-secret-key-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 15  # Magic link token expiration
    
    def get_cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]
    
    class Config:
        env_file = ".env"
        case_sensitive = False

    @field_validator("openai_api_key")
    @classmethod
    def _validate_openai_api_key(cls, v: str) -> str:
        # Key format depends on provider/base_url:
        # - OpenAI keys typically start with "sk-"
        # - OpenRouter keys typically start with "sk-or-"
        # We validate against base_url later (after both fields are set).
        return v

    @field_validator("openai_base_url")
    @classmethod
    def _validate_openai_base_url(cls, v: str) -> str:
        # Always require a URL-looking value.
        if v:
            parsed = urlparse(v)
            if not parsed.scheme or not parsed.netloc:
                raise ValueError("OPENAI_BASE_URL must be a valid URL (e.g., https://api.openai.com/v1)")
        return v

    @field_validator("llm_provider")
    @classmethod
    def _validate_llm_provider(cls, v: str) -> str:
        v2 = (v or "").strip().lower()
        if v2 not in {"openai", "openrouter"}:
            raise ValueError("LLM_PROVIDER must be 'openai' or 'openrouter'")
        return v2

    @field_validator("openai_model")
    @classmethod
    def _validate_model_for_provider(cls, v: str) -> str:
        # Keep this permissive; model naming differs by provider.
        # For OpenRouter, prefer names like "openai/gpt-4o" rather than "gpt-4o".
        return v

    @field_validator("openrouter_referer")
    @classmethod
    def _strip_openrouter_referer(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("openrouter_title")
    @classmethod
    def _strip_openrouter_title(cls, v: str) -> str:
        return (v or "").strip()

    @field_validator("openai_api_key", mode="after")
    @classmethod
    def _validate_key_against_base_url(cls, v: str, info):
        # Cross-field validation: requires openai_base_url to be present.
        data = info.data or {}
        base_url = (data.get("openai_base_url") or "").lower()
        provider = (data.get("llm_provider") or "").lower()

        if provider == "openrouter" or "openrouter.ai" in base_url:
            if v and not v.startswith("sk-or-"):
                raise ValueError("For OpenRouter, OPENAI_API_KEY should start with 'sk-or-'")
        else:
            if v and v.startswith("sk-or-"):
                raise ValueError("OPENAI_API_KEY looks like an OpenRouter key (sk-or-...), but base_url/provider is OpenAI")
            if v and not v.startswith("sk-"):
                raise ValueError("For OpenAI, OPENAI_API_KEY should start with 'sk-'")
        return v


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()

