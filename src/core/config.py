from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
EXCEL_DIR = BASE_DIR / 'excel'
EXCEL_DIR.mkdir(parents=True, exist_ok=True)

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    DB_HOST: str
    DB_PORT: int
    DB_USER: str
    DB_PASS: str
    DB_NAME: str
    DB_PGA_EMAIL: str
    DB_PGA_PASSWORD: str
    DB_PGA_PORT: int
    DB_URL: str
    DEBUG: bool

    model_config = SettingsConfigDict(env_file=Path(BASE_DIR,'.env'), env_file_encoding='utf-8')


# .env is runed once and cashed
@lru_cache()
def get_settings() -> Settings:
    return Settings()

# settings = get_settings()


if __name__ == '__main__':
    print(f'{BASE_DIR=}')

    settings = get_settings()
    print(settings)