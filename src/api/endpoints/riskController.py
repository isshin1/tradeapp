from fastapi import APIRouter
from conf.config import riskManagement
# from services.pihole import pihole
router = APIRouter()



@router.get("/api/pnl")
async def pnl():
    return riskManagement.pnl

@router.get("/api/killswitch")
async def killswitch():
    return riskManagement.endSession()


@router.post("/api/endSession")
async def endSession():
    return riskManagement.endSession(force=False)
#
# @router.get("/api/enablePihole")
# async def enablePihole():
#     return pihole.enablePihole()
#
# @router.get("/api/disablePihole")
# async def disablePihole():
#     return pihole.disablePihole()
#
# @router.post("/api/blockForDuration")
# async def disablePihole():
#     return pihole.blockForDuration()