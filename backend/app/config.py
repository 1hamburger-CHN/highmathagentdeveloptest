from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    spark_api_password: str = ""
    spark_api_base: str = "https://spark-api-open.xf-yun.com/v1/chat/completions"
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com/v1/chat/completions"

    chroma_persist_dir: str = "./data/chromadb"
    embedding_model: str = "BAAI/bge-m3"

    database_url: str = "sqlite:///./data/tutor.db"

    max_retries: int = 2
    api_timeout: int = 15
    sympy_timeout: int = 5

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
