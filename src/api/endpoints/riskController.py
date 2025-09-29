from typing import Annotated

from fastapi import APIRouter, Depends
from core.dependencies import get_risk_management, get_dhan_websocket# from conf.config import riskManagement
from core.auth import role_checker  # import role_checker from main.py
# from services.pihole import pihole
router = APIRouter()



@router.get("/api/pnl")
async def pnl(
        risk_service: Annotated[object, Depends(get_risk_management)],
        check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    return risk_service.pnl

@router.get("/api/killswitch")
async def killswitch(
        risk_service: Annotated[object, Depends(get_risk_management)],
        check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    return risk_service.endSession()


@router.post("/api/endSession")
async def endSession(
        risk_service: Annotated[object, Depends(get_risk_management)],
        check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    return risk_service.endSession(force=False)
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