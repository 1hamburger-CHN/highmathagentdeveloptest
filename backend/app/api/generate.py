from fastapi import APIRouter

router = APIRouter()


@router.post("/resource")
async def generate_resource(payload: dict):
    resource_type = payload.get("type", "lecture")
    concept = payload.get("concept", "")
    return {"type": resource_type, "concept": concept, "status": "generated"}
