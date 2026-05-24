from pathlib import Path

from pydantic_settings import BaseSettings

_PROJECT_ROOT = Path(__file__).parent.parent


class Settings(BaseSettings):
    spark_api_password: str = ""
    spark_api_base: str = "https://spark-api-open.xf-yun.com/v1/chat/completions"
    deepseek_api_key: str = ""
    deepseek_api_base: str = "https://api.deepseek.com/v1/chat/completions"

    chroma_persist_dir: str = str(_PROJECT_ROOT / "data" / "chromadb")
    embedding_model: str = "BAAI/bge-m3"

    # Turso (managed libsql/SQLite)
    turso_url: str = "libsql://socratic-tutor-1hamburger-chn.aws-ap-northeast-1.turso.io"
    turso_token: str = "eyJhbGciOiJFZERTQSIsInR5cCI6IkpXVCJ9.eyJhIjoicnciLCJnaWQiOiJjNDEwZjEwYi04YjNkLTRhOTMtYmRlYS03YTA4OGU1MDBlZGIiLCJpYXQiOjE3Nzk1MTIyMjEsInJpZCI6IjkzMjFlNTFhLTZlYTAtNDNlMi1hMWM0LWIzMWYxMzhlNDhiNSJ9.abzbqgkAWMMyvDU2hlrpXfzsub-cFJasUI3nLev2d4qyoLhxEdQEOQWAOLtACo0rFKq81ir2xVG1x8akzhIeCw"

    max_retries: int = 2
    api_timeout: int = 120
    sympy_timeout: int = 5

    model_config = {"env_file": str(_PROJECT_ROOT / ".env"), "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
