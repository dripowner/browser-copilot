"""Configuration management using Pydantic and environment variables."""

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    """Application configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # LLM Configuration (OpenAI-compatible API)
    llm_api_key: str = Field(..., description="API key for LLM provider")
    llm_base_url: str = Field(
        default="https://api.openai.com/v1",
        description="Base URL for OpenAI-compatible API",
    )
    llm_model: str = Field(default="gpt-4", description="Model name")
    llm_temperature: float = Field(
        default=0.0, ge=0.0, le=2.0, description="Temperature"
    )

    # Logging
    log_level: str = Field(default="INFO", description="Logging level")


def load_config(env_file: Optional[Path] = None) -> Config:
    """
    Load configuration from environment variables and .env file.

    Args:
        env_file: Optional path to .env file. If None, looks for .env in current directory.

    Returns:
        Config instance with loaded settings.
    """
    if env_file:
        os.environ["ENV_FILE"] = str(env_file)

    return Config()
