FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Auto-index knowledge base if ChromaDB is empty, then start server
EXPOSE 8000
CMD python -c "from app.main import auto_index_on_startup; auto_index_on_startup()" && uvicorn app.main:app --host 0.0.0.0 --port 8000
