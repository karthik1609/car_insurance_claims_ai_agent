"""
Configuration settings for the application
"""
import os
from pydantic import Field
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings(BaseSettings):
    """Application settings"""
    # API Configuration
    API_TITLE: str = "Car Insurance Claims AI Agent"
    API_VERSION: str = "1.0.0"
    
    # Groq Configuration
    GROQ_API_KEY: str = Field(default=os.getenv("GROQ_API_KEY", ""))
    GROQ_MODEL: str = Field(default=os.getenv("GROQ_MODEL", "meta-llama/llama-4-maverick-17b-128e-instruct"))
    
    # API Configuration
    API_HOST: str = Field(default=os.getenv("API_HOST", "0.0.0.0"))
    API_PORT: int = Field(default=int(os.getenv("API_PORT", 8000)))
    DEBUG_MODE: bool = Field(default=os.getenv("DEBUG_MODE", "true").lower() == "true")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings() 