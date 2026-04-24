from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AGENTROOMS_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://agentrooms:agentrooms@localhost:5435/agentrooms"


settings = Settings()
