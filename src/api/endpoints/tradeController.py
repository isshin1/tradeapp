from fastapi import APIRouter, HTTPException
from services.tradeManagement import refreshTrade
from conf.config import logger
router = APIRouter()


@router.post("/api/refreshTrade")
async def update_targets():
    try:
        refreshTrade()
    except Exception as e:
        logger.error(f'got exception in refreshTrade {e}')