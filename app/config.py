from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    REDIS_URL: str
    SECRET_KEY: str
    EMAIL_FROM: str
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

settings = Settings()
