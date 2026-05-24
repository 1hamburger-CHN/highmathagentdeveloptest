"""Spark Image Understanding API via WebSocket (wss://spark-api.../v2.1/image).

HMAC-SHA256 signature auth, WebSocket streaming, base64 image support.
"""
import base64
import hashlib
import hmac
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from urllib.parse import urlencode, urlparse

from app.config import settings

logger = logging.getLogger("tutor.spark_image")

_SPARK_IMAGE_URL = settings.spark_image_api_url


def _build_auth_url() -> str:
    """Build authenticated WebSocket URL with HMAC-SHA256 signature."""
    host = urlparse(_SPARK_IMAGE_URL).netloc
    # Manually build RFC 1123 date — strftime %b is locale-dependent
    MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    now = datetime.now(timezone.utc)
    ts = f"{DAYS[now.weekday()]}, {now.day:02d} {MONTHS[now.month-1]} {now.year} {now.hour:02d}:{now.minute:02d}:{now.second:02d} GMT"

    # Signature string per Spark WebSocket spec
    path = urlparse(_SPARK_IMAGE_URL).path or "/v2.1/image"
    sig_raw = f"host: {host}\ndate: {ts}\nGET {path} HTTP/1.1"
    sig = base64.b64encode(
        hmac.new(
            settings.spark_image_api_secret.encode(),
            sig_raw.encode(),
            hashlib.sha256,
        ).digest()
    ).decode()

    # Authorization header
    auth_raw = (
        f'api_key="{settings.spark_image_api_key}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{sig}"'
    )
    auth_b64 = base64.b64encode(auth_raw.encode()).decode()

    params = urlencode({
        "authorization": auth_b64,
        "date": ts,
        "host": host,
    })
    url = f"{_SPARK_IMAGE_URL}?{params}"
    logger.info(f"Spark Image Auth: host={host} date={ts}")
    logger.info(f"Spark Image Auth: sig_raw={sig_raw!r}")
    logger.info(f"Spark Image Auth: api_key first 20 chars={settings.spark_image_api_key[:20]}...")
    return url


async def spark_image_chat(
    image_data: str,       # base64 or data URL
    prompt: str,
    timeout: int = 60,
) -> str:
    """Send image + prompt to Spark Image API via WebSocket, return response text."""
    # Normalize image data — strip data URL prefix if present
    if image_data.startswith("data:"):
        image_data = image_data.split(",", 1)[1]

    ws_url = _build_auth_url()
    logger.info(f"Spark Image WS URL: {ws_url[:120]}...")

    request_id = uuid.uuid4().hex
    payload = {
        "header": {"app_id": settings.spark_image_app_id, "uid": request_id},
        "parameter": {
            "chat": {
                "domain": "imagev3",
                "temperature": 0.5,
                "max_tokens": 2048,
            }
        },
        "payload": {
            "message": {
                "text": [
                    {
                        "role": "user",
                        "content": prompt,
                        "content_type": "image",
                        "content_url": f"data:image/jpeg;base64,{image_data}",
                    }
                ]
            }
        },
    }

    try:
        import websockets
    except ImportError:
        logger.error("websockets not installed; cannot call Spark Image API")
        return "图片理解服务暂不可用（缺少 websockets 依赖）。"

    full_response = []
    status = 0  # 0=first, 1=streaming, 2=complete

    try:
        async with websockets.connect(ws_url, open_timeout=timeout) as ws:
            await ws.send(json.dumps(payload, ensure_ascii=False))

            while True:
                raw = await ws.recv()
                data = json.loads(raw)

                header = data.get("header", {})
                code = header.get("code", 0)
                sid = header.get("sid", "")

                if code != 0:
                    msg = header.get("message", f"Spark Image API error {code}")
                    logger.error(f"Spark Image API error: code={code} msg={msg}")
                    return f"图片理解出错：{msg}"

                payload_data = data.get("payload", {})
                choices = payload_data.get("choices", {})
                text_list = choices.get("text", [])

                for t in text_list:
                    content = t.get("content", "")
                    if content:
                        full_response.append(content)

                status = header.get("status", 0)
                if status == 2:  # complete
                    break

    except Exception as e:
        logger.exception(f"Spark Image WebSocket error: {e}")
        return f"图片理解连接失败：{e}"

    return "".join(full_response)
