from fastapi import APIRouter
from fastapi.responses import FileResponse

router = APIRouter(tags=["WebSocket Docs"])

#Возвращает спецификацию WebSocket API (AsyncAPI).
@router.get("/ws/docs", include_in_schema=False)
async def get_asyncapi_spec():
    return FileResponse("docs/asyncapi.yaml")
