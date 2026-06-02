import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Enterprise Knowledge Intelligence Platform"
    DEBUG: bool = False
    
    # API Keys
    GROQ_API_KEY: str = Field(default="", validation_alias="GROQ_API_KEY")
    OPENAI_API_KEY: str = Field(default="", validation_alias="OPENAI_API_KEY")
    
    # Databases
    DATABASE_URL: str = Field(default="sqlite:///./rag_platform.db", validation_alias="DATABASE_URL")
    CHROMA_PERSIST_DIR: str = Field(default="./data/chroma_db", validation_alias="CHROMA_PERSIST_DIR")
    
    # Models Configuration
    EMBEDDING_MODEL: str = Field(default="BAAI/bge-large-en-v1.5", validation_alias="EMBEDDING_MODEL")
    RERANKER_MODEL: str = Field(default="cross-encoder/ms-marco-MiniLM-L-6-v2", validation_alias="RERANKER_MODEL")
    
    # LLM Settings
    GROQ_DEFAULT_MODEL: str = Field(default="llama-3.3-70b-versatile", validation_alias="GROQ_DEFAULT_MODEL")
    TEMPERATURE: float = 0.1
    MAX_TOKENS: int = 4096
    
    # Monitoring
    LANGCHAIN_TRACING_V2: str = Field(default="false", validation_alias="LANGCHAIN_TRACING_V2")
    LANGCHAIN_API_KEY: str = Field(default="", validation_alias="LANGCHAIN_API_KEY")
    LANGCHAIN_PROJECT: str = Field(default="enterprise-rag-platform", validation_alias="LANGCHAIN_PROJECT")
    
    # Ingestion Configuration
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: list = ["pdf", "docx", "txt", "csv", "xlsx", "xls", "md", "html"]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Create a global settings instance
settings = Settings()
