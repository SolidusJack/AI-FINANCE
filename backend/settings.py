from pydantic_settings import BaseSettings, SettingsConfigDict


class ConfigEnv(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    URL_DATABASE: str = ""
    OPENROUTER_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    OPENROUTER_MODEL: str = "nvidia/nemotron-3-ultra-550b-a55b:free"

Settings = ConfigEnv()