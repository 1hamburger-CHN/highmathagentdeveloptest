"""Manim renderer — temp file + CLI subprocess with heartbeat and file lock."""

import asyncio
import hashlib
import json
import logging
import os
import tempfile
from pathlib import Path

from app.animation.base import BaseManimTemplate
from app.animation.schema import AnimationResource

logger = logging.getLogger("tutor.animation")

RENDER_TIMEOUT = 120  # seconds
HEARTBEAT_INTERVAL = 2  # seconds
OUTPUT_DIR = Path("static/animations")


class ManimRenderer:
    """Renders Manim templates to mp4 via subprocess, with caching."""

    def __init__(self, heartbeat_queue: asyncio.Queue | None = None):
        self._lock = asyncio.Lock()
        self._heartbeat_queue = heartbeat_queue
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    async def render(
        self, template: BaseManimTemplate, params: dict,
    ) -> AnimationResource | None:
        """Render template with params to mp4. Returns None on failure."""

        # ——— Cache check ———
        cache_key = self._cache_key(template.template_name, params)
        cache_path = OUTPUT_DIR / f"{template.template_name}_{cache_key}.mp4"
        if cache_path.exists():
            logger.info(f"Animation cache hit: {cache_path}")
            return AnimationResource(
                mp4_url=f"/animations/{cache_path.name}",
                title=f"{template.template_name} 动画",
                template_used=template.template_name,
                params=params,
            )

        # ——— File lock (single concurrent render) ———
        acquired = self._lock.locked()
        if acquired:
            logger.warning("Render already in progress, rejecting")
            return None

        async with self._lock:
            return await self._do_render(template, params, cache_path)

    # ----------------------------------------------------------------
    # Internal
    # ----------------------------------------------------------------

    async def _do_render(
        self, template: BaseManimTemplate, params: dict, cache_path: Path,
    ) -> AnimationResource | None:
        """Run the full render pipeline with heartbeat and timeout."""
        await self._push_heartbeat("animation_start", {"template": template.template_name})

        # 1. Generate scene code
        try:
            scene_code = template.build_scene_code(params)
        except Exception as exc:
            logger.error(f"build_scene_code failed: {exc}")
            await self._push_heartbeat("animation_failed", {"reason": "code_generation"})
            return None

        # 2. Write temp file
        tmp_path = None
        try:
            tmp_path = self._write_temp_file(scene_code)
        except Exception as exc:
            logger.error(f"Write temp file failed: {exc}")
            await self._push_heartbeat("animation_failed", {"reason": "temp_file"})
            return None

        # 3. Render
        try:
            await self._run_manim(tmp_path, template.scene_class_name)
        except asyncio.TimeoutError:
            logger.error(f"Render timed out after {RENDER_TIMEOUT}s")
            await self._push_heartbeat("animation_failed", {"reason": "timeout"})
            return None
        except Exception as exc:
            logger.error(f"Manim render failed: {exc}")
            await self._push_heartbeat("animation_failed", {"reason": "render_error"})
            return None
        finally:
            self._cleanup(tmp_path)

        # 4. Find and move rendered mp4
        mp4_path = self._find_output(template.scene_class_name)
        if mp4_path is None:
            logger.error("Manim output mp4 not found")
            await self._push_heartbeat("animation_failed", {"reason": "missing_output"})
            return None

        mp4_path.rename(cache_path)
        await self._push_heartbeat("animation_done", {
            "url": f"/static/animations/{cache_path.name}",
        })
        return AnimationResource(
            mp4_url=f"/animations/{cache_path.name}",
            title=f"{template.template_name} 动画",
            template_used=template.template_name,
            params=params,
        )

    async def _run_manim(self, script_path: Path, scene_name: str) -> None:
        """Run manim CLI with heartbeat, raising TimeoutError on timeout."""
        heartbeat_task = asyncio.create_task(self._heartbeat_loop())

        try:
            proc = await asyncio.create_subprocess_exec(
                "manim", "-pql", str(script_path), scene_name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                await asyncio.wait_for(proc.communicate(), timeout=RENDER_TIMEOUT)
                if proc.returncode != 0:
                    stderr = (await proc.stderr.read()).decode() if proc.stderr else ""
                    raise RuntimeError(f"Manim exit {proc.returncode}: {stderr[-300:]}")
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                raise
        finally:
            heartbeat_task.cancel()
            try:
                await heartbeat_task
            except asyncio.CancelledError:
                pass

    async def _heartbeat_loop(self) -> None:
        """Push heartbeat events to SSE queue every HEARTBEAT_INTERVAL seconds."""
        if self._heartbeat_queue is None:
            return
        elapsed = 0
        while True:
            await asyncio.sleep(HEARTBEAT_INTERVAL)
            elapsed += HEARTBEAT_INTERVAL
            await self._push_heartbeat("animation_rendering", {"elapsed": elapsed})

    async def _push_heartbeat(self, event: str, data: dict) -> None:
        """Push an event to the SSE queue if available."""
        if self._heartbeat_queue is not None:
            try:
                self._heartbeat_queue.put_nowait({"event": event, "data": data})
            except asyncio.QueueFull:
                pass

    # ----------------------------------------------------------------
    # Helpers
    # ----------------------------------------------------------------

    @staticmethod
    def _write_temp_file(code: str) -> Path:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", prefix="manim_", delete=False,
            encoding="utf-8",
        )
        tmp.write(code)
        tmp.close()
        return Path(tmp.name)

    @staticmethod
    def _find_output(scene_name: str) -> Path | None:
        """Find the mp4 produced by manim. Manim outputs to ./media/videos/<script>/480p15/<Scene>.mp4."""
        media_dir = Path("media/videos")
        if not media_dir.exists():
            return None
        for mp4 in media_dir.rglob(f"{scene_name}.mp4"):
            return mp4
        return None

    @staticmethod
    def _cleanup(tmp_path: Path | None) -> None:
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass

    @staticmethod
    def _cache_key(template_name: str, params: dict) -> str:
        raw = json.dumps({"t": template_name, "p": params}, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
