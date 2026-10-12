from pydantic_settings import BaseSettings,SettingsConfigDict

class ConfigEnv(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env",env_file_encoding="utf-8")
    URL_DATABASE: str = ''
    OPENROUTER_API_KEY: str = ''

Settings = ConfigEnv()