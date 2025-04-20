from fastapi import APIRouter
from services.pihole import pihole
router = APIRouter()



@router.get("/api/pnl")
async def pnl():
    return riskManagementobj.pnl

@router.get("/api/killswitch")
async def killswitch():
    return riskManagementobj.killswitch()


@router.post("/api/endSession")
async def endSession():
    return riskManagementobj.endSession()
#
# @router.get("/api/enablePihole")
# async def enablePihole():
#     return pihole.enablePihole()
#
@router.get("/api/disablePihole")
async def disablePihole():
    return pihole.disablePihole()
#
# @router.post("/api/blockForDuration")
# async def disablePihole():
#     return pihole.blockForDuration()