from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    allowed_origins: str
    database_url: str
    supabase_url: str
    supabase_anon_key: str
    gemini_api_key: str | None = None
    google_api_key: str | None = None
    embedding_model: str = "text-embedding-004"
    embedding_dimension: int = 1536
    llm_model: str = "gemini-2.5-flash"

    @property
    def effective_gemini_api_key(self) -> str | None:
        return self.gemini_api_key or self.google_api_key


settings = Settings()
