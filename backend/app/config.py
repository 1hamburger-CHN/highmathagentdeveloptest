from pathlib import Path

from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    spark_api_password: str = ""
    spark_api_base: str = "https://spark-api-open.xf-yun.com/v1/chat/completions"
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com/v1/chat/completions"

    # Spark Image Understanding API (WebSocket)
    spark_image_app_id: str = ""
    spark_image_api_key: str = ""
    spark_image_api_secret: str = ""
    spark_image_api_url: str = "wss://spark-api.cn-huabei-1.xf-yun.com/v2.1/image"

    chroma_persist_dir: str = str(_PROJECT_ROOT / "data" / "chromadb")
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Turso (managed libsql/SQLite)
    turso_url: str = ""
    turso_token: str = ""

    max_retries: int = 2
    api_timeout: int = 120
    sympy_timeout: int = 5

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
