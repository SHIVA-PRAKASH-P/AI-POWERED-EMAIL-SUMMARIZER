from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import List

class Settings(BaseSettings):
    APP_NAME: str = "AI Email Summarizer Agent for Faculty"
    APP_ENV: str = "development"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "127.0.0.1"
    
    DATABASE_URL: str = "sqlite:///./backend/app/database/email_agent.db"
    
    AI_MODE: str = "mock"
    LLM_PROVIDER: str = "openai"
    LLM_API_KEY: str = ""
    LLM_MODEL: str = "gpt-4o-mini"
    LLM_BASE_URL: str = ""
    LLM_TEMPERATURE: float = 0.0
    LLM_MAX_TOKENS: int = 1500
    LLM_TIMEOUT: float = 30.0
    LLM_FALLBACK_ON_ERROR: bool = True
    
    # Modular Email Ingestion Provider
    EMAIL_PROVIDER: str = "mock"  # Options: "mock", "gmail"
    GMAIL_CLIENT_ID: str = ""
    GMAIL_CLIENT_SECRET: str = ""
    GMAIL_REFRESH_TOKEN: str = ""
    GMAIL_CREDENTIALS_PATH: str = ""
    GMAIL_TOKEN_PATH: str = "./backend/app/database/gmail_token.json"
    
    # Google OAuth 2.0 (Stage 19A — College Gmail Integration)
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://127.0.0.1:8000/api/email-provider/gmail/oauth/callback"
    COLLEGE_GMAIL_ACCOUNT: str = "shivaprakashp.cs24@bitsathy.ac.in"
    GMAIL_SCOPES: str = "https://www.googleapis.com/auth/gmail.readonly"
    
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    SECRET_KEY: str = "dev-secret-key"
    MAX_PAYLOAD_BYTES: int = 5 * 1024 * 1024  # 5 Megabytes

    @model_validator(mode="after")
    def validate_production_security(self) -> 'Settings':
        """Enforce strict security standards when running in production environment."""
        if self.APP_ENV.lower() == "production":
            # Force DEBUG to False in production
            self.DEBUG = False
            if self.SECRET_KEY == "dev-secret-key" or len(self.SECRET_KEY) < 16:
                raise ValueError(
                    "Production deployment requires a secure, non-default SECRET_KEY with at least 16 characters."
                )
        return self

    @property
    def is_production(self) -> bool:
        return self.APP_ENV.lower() == "production"

    @property
    def masked_api_key(self) -> str:
        """Return masked API key for telemetry without exposing raw secret."""
        if not self.LLM_API_KEY:
            return "Not Configured"
        if len(self.LLM_API_KEY) <= 8:
            return "********"
        return f"{self.LLM_API_KEY[:4]}...{self.LLM_API_KEY[-4:]}"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    @property
    def resolved_google_client_id(self) -> str:
        return self.GOOGLE_CLIENT_ID or self.GMAIL_CLIENT_ID

    @property
    def resolved_google_client_secret(self) -> str:
        return self.GOOGLE_CLIENT_SECRET or self.GMAIL_CLIENT_SECRET

    @property
    def resolved_google_redirect_uri(self) -> str:
        return self.GOOGLE_REDIRECT_URI

    @property
    def is_google_oauth_configured(self) -> bool:
        return bool(self.resolved_google_client_id and self.resolved_google_client_secret)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

def get_settings() -> Settings:
    return settings
