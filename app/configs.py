from pydantic_settings import BaseSettings, SettingsConfigDict


DOTENV_PATH = "configs/.env"




class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=DOTENV_PATH)
    MAX_RESULTS: int
    CHAT_MODEL_NAME: str
    DEEPSEEK_OCR_MODEL_NAME: str

    ARXIV_PROMPT_PATH: str

    PAPERS_DIR: str
    BOOKS_DIR: str
    SQLITE_CHECKPOINTS_URI: str



settings = Settings()