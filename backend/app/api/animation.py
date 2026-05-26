"""Animation API endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/animation", tags=["animation"])


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
