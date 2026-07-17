"""Animation API endpoints."""

from pathlib import Path

from fastapi import APIRouter

router = APIRouter(prefix="/api/animation", tags=["animation"])


@router.get("/list")
async def list_animations():
    """List rendered Manim animations."""
    anim_dir = Path("static/animations")
    if not anim_dir.exists():
        return {"animations": []}
    animations = []
    for mp4 in sorted(anim_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        template_name = mp4.name.split("_")[0]
        animations.append({
            "name": mp4.name,
            "url": f"/animations/{mp4.name}",
            "template": template_name,
            "size_kb": round(mp4.stat().st_size / 1024),
            "created_at": mp4.stat().st_mtime,
        })
    return {"animations": animations}


@router.post("/generate")
async def trigger_animation(request: dict):
    """Trigger animation generation for a concept.

    This endpoint is primarily for testing / manual trigger.
    In normal flow, animation is triggered automatically by the coach.
    """
    return {
        "animation_id": "not-implemented",
        "status": "queued",
        "message": "Animation generation is triggered automatically via the coach flow. "
                   "Use POST /api/chat/stream to interact with the tutor.",
    }


@router.get("/{animation_id}/status")
async def animation_status(animation_id: str):
    """Query animation render status."""
    return {
        "animation_id": animation_id,
        "status": "unknown",
        "message": "Status tracking requires persistent animation store (future work).",
    }
