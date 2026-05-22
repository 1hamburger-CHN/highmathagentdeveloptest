from fastapi import APIRouter

router = APIRouter()


@router.post("/submit")
async def submit_assessment(payload: dict):
    return {"status": "evaluated", "result": {}}
