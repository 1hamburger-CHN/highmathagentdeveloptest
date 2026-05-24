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
from time import mktime
from urllib.parse import urlencode, urlparse
from wsgiref.handlers import format_date_time

from app.config import settings

logger = logging.getLogger("tutor.spark_image")

_SPARK_IMAGE_URL = settings.spark_image_api_url


def _build_auth_url() -> str:
    """Build authenticated WebSocket URL — per official Spark docs."""
    host = urlparse(_SPARK_IMAGE_URL).netloc
    path = urlparse(_SPARK_IMAGE_URL).path

    # Step 1: RFC 1123 date
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))

    # Signature string
    tmp = f"host: {host}\n"
    tmp += f"date: {date}\n"
    tmp += f"GET {path} HTTP/1.1"

    # HMAC-SHA256
    tmp_sha = hmac.new(
        settings.spark_image_api_secret.strip().encode("utf-8"),
        tmp.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).digest()

    # Base64 signature
    signature = base64.b64encode(tmp_sha).decode("utf-8")

    # Authorization per official docs: base64(authorization_origin)
    authorization_origin = (
        f'api_key="{settings.spark_image_api_key}", '
        f'algorithm="hmac-sha256", '
        f'headers="host date request-line", '
        f'signature="{signature}"'
    )
    authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")

    # Final URL per official docs
    v = {
        "authorization": authorization,
        "date": date,
        "host": host,
    }
    url = f"wss://{host}{path}?{urlencode(v)}"
    logger.info(f"=== Spark Image Auth Debug ===")
    logger.info(f"APP_ID:        {settings.spark_image_app_id}")
    logger.info(f"API_KEY:       {settings.spark_image_api_key[:8]}...{settings.spark_image_api_key[-4:] if len(settings.spark_image_api_key) > 12 else ''}")
    logger.info(f"API_SECRET:    {settings.spark_image_api_secret[:8]}...{settings.spark_image_api_secret[-4:] if len(settings.spark_image_api_secret) > 12 else ''}")
    logger.info(f"host: {host}")
    logger.info(f"date: {date}")
    logger.info(f"tmp:  {tmp!r}")
    logger.info(f"sig:  {signature}")
    logger.info(f"auth_origin: {authorization_origin}")
    sk = settings.spark_image_api_secret
    ak = settings.spark_image_api_key
    logger.info(f"SECRET(len={len(sk)}): {sk[:8] if len(sk)>=8 else sk}...{sk[-4:] if len(sk)>=4 else ''}")
    logger.info(f"KEY(len={len(ak)}):    {ak[:8] if len(ak)>=8 else ak}...{ak[-4:] if len(ak)>=4 else ''}")
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
        import websockets
    except ImportError:
        logger.error("websockets not installed")
        return "图片理解服务暂不可用（缺少 websockets 依赖）。"

    full_response = []

    try:
        async with websockets.connect(ws_url, open_timeout=timeout, ping_interval=None) as ws:
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
