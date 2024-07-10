from pydantic import BaseSettings
from dotenv import load_dotenv
import os
from functools import lru_cache


load_dotenv()  # load environment variables from .env file


class Settings(BaseSettings):
    database_url: str = os.getenv("database_url")
    # LOGIN_DATABASE_URL: str

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings():
    return Settings()
