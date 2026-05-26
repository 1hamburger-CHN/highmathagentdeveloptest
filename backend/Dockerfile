FROM python:3.11-slim

WORKDIR /app

# Use Tencent Cloud Debian mirror + install system deps for Manim
RUN sed -i 's/deb.debian.org/mirrors.tencent.com/g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ \
    ffmpeg \
    libcairo2-dev libpango1.0-dev pkg-config \
    texlive-latex-extra texlive-fonts-recommended \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# Use Tencent pip mirror
RUN pip install --no-cache-dir -i https://mirrors.cloud.tencent.com/pypi/simple -r requirements.txt

COPY . .

# Create static dirs
RUN mkdir -p /app/data/chromadb /app/backend/static/animations

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
