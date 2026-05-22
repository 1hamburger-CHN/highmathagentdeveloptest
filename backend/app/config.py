from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    spark_api_key: str = ""
    spark_api_secret: str = ""
    spark_app_id: str = ""
    deepseek_api_key: str = ""

    chroma_persist_dir: str = "./data/chromadb"
    embedding_model: str = "BAAI/bge-m3"

    database_url: str = "sqlite:///./data/tutor.db"

    max_retries: int = 2
    api_timeout: int = 15  # seconds
    sympy_timeout: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
