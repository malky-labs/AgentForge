from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "AgentForge"
    API_V1_STR: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "agentforge-super-secret-key-change-in-prod-123456"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440 # 24 hours
    
    # Database
    DATABASE_URL: str = "sqlite:///./agentforge.db"
    
    # Ollama Integration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    
    # ChromaDB
    CHROMA_DB_PATH: str = "./chroma_data"
    
    # Rate Limiting
    RATE_LIMIT_LIMIT: int = 100
    RATE_LIMIT_WINDOW_SECONDS: int = 60
    
    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://localhost:4317"
    OTEL_SERVICE_NAME: str = "agentforge-backend"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
