from fastapi import APIRouter, HTTPException
# from services.tradeManagement import refreshTrade
from conf.config import tradeManagement
from conf.logging_config import logger
from pydantic import BaseModel

router = APIRouter()


class TargetRequest(BaseModel):
    t1: float
    t2: float
    # t3: float


@router.post("/api/refreshTrade")
async def update_targets():
    try:
        tradeManagement.refreshTrade()
    except Exception as e:
        logger.error(f'got exception in refreshTrade {e}')

@router.post("/api/updateTargets")
async def update_targets(target_data: TargetRequest):
    try:
        # Extract target values from the request
        t1 = target_data.t1
        t2 = target_data.t2
        # t3 = target_data.t3

        # Process the target updates
        targets = dict()
        targets['t1'] = t1
        targets['t2'] = t2
        # targets['t3'] = t3
        tradeManagement.updateTargets(targets)

        # if result:
        #     return {"success": True, "message": "Your targets have been successfully updated."}
        # else:
        #     raise HTTPException(status_code=500, detail="Failed to update targets")
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=f"Error updating targets: {str(e)}")
