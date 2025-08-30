from fastapi import APIRouter, Depends
from conf.config import riskManagement
from core.auth import role_checker  # import role_checker from main.py
# from services.pihole import pihole
router = APIRouter()



@router.get("/api/pnl")
async def pnl(check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    return riskManagement.pnl

@router.get("/api/killswitch")
async def killswitch(check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    return riskManagement.endSession()


@router.post("/api/endSession")
async def endSession(check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
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