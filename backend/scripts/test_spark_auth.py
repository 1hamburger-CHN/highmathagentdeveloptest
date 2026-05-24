"""Quick test script to verify Spark Image API auth URL generation."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.spark_image import _build_auth_url
from app.config import settings

print("=== Spark Image Auth Test ===")
print(f"APP_ID:    {settings.spark_image_app_id}")
print(f"API_KEY:   {settings.spark_image_api_key[:20]}...")
print(f"API_SECRET:{settings.spark_image_api_secret[:20]}...")
print(f"API_URL:   {settings.spark_image_api_url}")
print()

url = _build_auth_url()
print(f"Auth URL (first 200 chars):\n{url[:200]}")
print()

# Try WebSocket connection
import asyncio
import websockets
import json

async def test():
    print("Connecting...")
    try:
        async with websockets.connect(
            url,
            open_timeout=15,
            ping_interval=None,
            extra_headers={"Host": "spark-api.cn-huabei-1.xf-yun.com"},
        ) as ws:
            print("Connected!")
            await ws.send(json.dumps({"header": {"app_id": settings.spark_image_app_id}, "parameter": {"chat": {"domain": "imagev3"}}, "payload": {"message": {"text": [{"role": "user", "content": "test", "content_type": "text"}]}}}))
            resp = await asyncio.wait_for(ws.recv(), timeout=10)
            print(f"Response: {resp[:200]}")
    except websockets.InvalidStatus as e:
        print(f"WebSocket rejected: {e.response.status_code}")
        print(f"Response headers: {dict(e.response.headers)}")
        print(f"Response body: {e.response.body[:500] if e.response.body else 'empty'}")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")

asyncio.run(test())
