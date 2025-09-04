from fastapi import APIRouter, HTTPException, Depends
from conf.config import dhan_api
# from services.optionUpdate import optionUpdateObj
# from services.tradeManagement import updateOpenOrders
from conf.config import optionUpdate,  tradeManagement
from pydantic import BaseModel
from schemas.planSchema import PlanSchema
from conf.config import decisionPoints
from datetime import date
from conf.config import db_helper
from sqlalchemy.orm import Session
from conf.config import *
from conf.config import dhan_api
from conf.logging_config import logger
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any
from core.auth import role_checker  # import role_checker from main.py
router = APIRouter()

@router.post("/api/firstFetch")
async def firstFetch():
    optionUpdate.updateOptions(firstFetch=True)
    tradeManagement.updateOpenOrders()

@router.get("/api/margin")
async def getMargin(check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    return dhan_api.get_balance()


@router.get("/api/getDps")
async def getDps():
    return decisionPoints.get_decision_points()

@router.delete("/api/deleteDp/{name}/{price}")
async def deleteDp(name:str, price:int, check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    return decisionPoints.deleteDp(name, price)

@router.put("/api/updateDp/{price}/{new_price}")
async def updateDp(price:int, new_price:int, check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    return decisionPoints.updateDp(price, new_price)


class TradePlanRequest(BaseModel):
    date: date

class TradePlanUpdate(BaseModel):
    plan: str
@router.get("/api/tradePlan")
def get_plan(date: date, db: Session = Depends(db_helper.get_db)) -> Dict[str, str]:
    try:
        date = date.strftime("%Y-%m-%d")
        return db_helper.get_plan(db, date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/tradePlan", response_model=PlanSchema)
def create_or_update_plan(plan: PlanSchema, db: Session = Depends(db_helper.get_db), check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    try:
        db_plan = db_helper.add_or_update_plan(db, plan)
        return db_plan
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))




@router.get("/api/fetchHistoricalData/{tsym}")
def fetch_historical_data(tsym: str) -> List[Dict[str, Any]]:
    # Get the token for the given symbol
    print(f"Fetching historical data for symbol {tsym}")
    token = dhan_api.get_token(tsym)

    # Calculate the start time (1 week ago, beginning of day)
    starttime = int(
        (datetime.now(timezone.utc) - timedelta(weeks=1))
        .replace(hour=0, minute=0, second=0, microsecond=0)
        .timestamp()
    )

    # Get the time price series data
    res = shoonya_api. get_time_price_series("NFO", str(token), str(starttime), None, "3")

    # Convert result to list of dicts (reversed, like in Java)
    data_list: List[Dict[str, Any]] = []
    if res ==  None:
        return []
    for obj in reversed(res):
        data_map = {
            "into": obj.get("into"),
            "stat": obj.get("stat"),
            "ssboe": obj.get("ssboe"),
            "intvwap": obj.get("intvwap"),
            "intoi": obj.get("intoi"),
            "intc": obj.get("intc"),
            "intv": obj.get("intv"),
            "v": obj.get("v"),
            "inth": obj.get("inth"),
            "oi": obj.get("oi"),
            "time": obj.get("time"),
            "intl": obj.get("intl"),
        }
        data_list.append(data_map)
    data_list.sort(key=lambda x: x['ssboe'])

    seen_ssboe = set()
    filtered_data_list = []

    for entry in data_list:
        ssboe_value = entry.get("ssboe")
        if ssboe_value not in seen_ssboe:
            filtered_data_list.append(entry)
            seen_ssboe.add(ssboe_value)

    return filtered_data_list





