"""Spark Image Understanding API via WebSocket (wss://spark-api.../v2.1/image).

HMAC-SHA256 signature auth per official Spark WebSocket spec.
"""
import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import datetime
from email.utils import formatdate
from urllib.parse import quote, urlparse

from app.config import settings

logger = logging.getLogger("tutor.spark_image")

_SPARK_IMAGE_URL = settings.spark_image_api_url


def _build_auth_url() -> str:
    """Build authenticated WebSocket URL per Spark official sample code."""
    host = urlparse(_SPARK_IMAGE_URL).netloc
    path = urlparse(_SPARK_IMAGE_URL).path

    # RFC 1123 date
    date = formatdate(timeval=None, localtime=False, usegmt=True)

    # Signature string
    tmp = f"host: {host}\n"
    tmp += f"date: {date}\n"
    tmp += f"GET {path} HTTP/1.1"

    # HMAC-SHA256
    tmp_sha = hmac.new(
        settings.spark_image_api_secret.encode("utf-8"),
        tmp.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    # Base64 signature
    signature = base64.b64encode(tmp_sha).decode("utf-8")

    # Authorization (raw, NOT base64 — URL-encoded directly per working sample)
    authorization_origin = (
        f'api_key="{settings.spark_image_api_key}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{signature}"'
    )

    # Final URL — authorization_origin is URL-encoded, NOT base64-encoded
    url = (
        f"wss://{host}{path}?"
        f"authorization={quote(authorization_origin)}"
        f"&date={quote(date)}"
        f"&host={quote(host)}"
    )
    logger.info(f"=== Spark Image Auth Debug ===")
    logger.info(f"APP_ID:        {settings.spark_image_app_id}")
    logger.info(f"API_KEY:       {settings.spark_image_api_key[:8]}...{settings.spark_image_api_key[-4:] if len(settings.spark_image_api_key) > 12 else ''}")
    logger.info(f"API_SECRET:    {settings.spark_image_api_secret[:8]}...{settings.spark_image_api_secret[-4:] if len(settings.spark_image_api_secret) > 12 else ''}")
    logger.info(f"host: {host}")
    logger.info(f"date: {date}")
    logger.info(f"tmp:  {tmp!r}")
    logger.info(f"sig:  {signature}")
    logger.info(f"auth_origin: {authorization_origin}")
    logger.info(f"FULL URL: {url}")
    return url


async def spark_image_chat(
    image_data: str,       # base64 or data URL
    prompt: str,
    timeout: int = 60,
) -> str:
    """Send image + prompt to Spark Image API via WebSocket, return response text."""
    if image_data.startswith("data:"):
        image_data = image_data.split(",", 1)[1]

    ws_url = _build_auth_url()
    logger.info(f"Spark Image FULL URL:\n{ws_url}")

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
        from websockets.client import connect as ws_connect
    except ImportError:
        logger.error("websockets not installed")
        return "图片理解服务暂不可用（缺少 websockets 依赖）。"

    full_response = []

    try:
        from urllib.parse import urlparse as _up, urlunparse
        p = _up(ws_url)
        # Rebuild URI preserving query string explicitly
        uri = urlunparse(("wss", p.netloc, p.path, "", p.query, ""))
        logger.info(f"Spark Image WS URI: {uri[:200]}...")
        async with ws_connect(uri, open_timeout=timeout, ping_interval=None) as ws:
            await ws.send(json.dumps(payload, ensure_ascii=False))

            while True:
                raw = await ws.recv()
                data = json.loads(raw)

                header = data.get("header", {})
                code = header.get("code", 0)

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

                if header.get("status") == 2:
                    break

    except Exception as e:
        detail = str(e)
        if hasattr(e, "response"):
            detail += f" | body: {getattr(e.response, 'body', b'')[:300]}"
        logger.exception(f"Spark Image WebSocket error: {detail}")
        return f"图片理解连接失败：{detail}"

    return "".join(full_response)
