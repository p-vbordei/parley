from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PARLEY_", env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://parley:parley@localhost:5435/parley"


settings = Settings()
