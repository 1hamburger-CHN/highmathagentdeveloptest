from fastapi import APIRouter

router = APIRouter()


@router.get("/{user_id}")
async def get_profile(user_id: str):
    return {"user_id": user_id, "profile": None}


@router.post("/{user_id}")
async def update_profile(user_id: str, payload: dict):
    return {"user_id": user_id, "status": "updated"}
