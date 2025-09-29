from fastapi import APIRouter, HTTPException, Depends, Request
# from conf.config import dhan_api
# from services.optionUpdate import optionUpdateObj
# from services.tradeManagement import updateOpenOrders
# from conf.config import optionUpdate,  tradeManagement
from pydantic import BaseModel
from schemas.planSchema import PlanSchema
# from conf.config import decisionPoints
from datetime import date
# from conf.config import db_helper
from sqlalchemy.orm import Session
from conf.config import *
# from conf.config import dhan_api
from conf.logging_config import logger
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Annotated
from core.auth import role_checker  # import role_checker from main.py
from core.dependencies import get_trade_management, get_option_update_service, get_dhan_api, get_shoonya_api, get_decision_points_manager, get_db_manager, get_dhan_helper
import pandas as pd
from datetime import datetime, date, timedelta

router = APIRouter()


@router.get("/callback")
async def dhan_callback(request: Request):
    token_id = request.query_params.get("tokenId")
    # Use token_id to get the access token
    return {"status": "received", "tokenId": token_id}



@router.post("/api/firstFetch")
async def firstFetch(
        option_update: Annotated[object, Depends(get_option_update_service)],
        trade_management: Annotated[object, Depends(get_trade_management)]
):
    option_update.updateOptions(firstFetch=True)
    trade_management.updateOpenOrders()

@router.get("/api/margin")
async def getMargin(
        dhan_helper: Annotated[object, Depends(get_dhan_helper)],
        check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))
):
    return dhan_helper.get_balance()


@router.get("/api/getDps")
async def getDps(
        decisionPoints: Annotated[object, Depends(get_decision_points_manager)],
        check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))
):
    return decisionPoints.get_decision_points()

@router.delete("/api/deleteDp/{name}/{price}")
async def deleteDp(
        name:str,
        price:int,
        decisionPoints: Annotated[object, Depends(get_decision_points_manager)],
        check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))
):
    return decisionPoints.deleteDp(name, price)

@router.put("/api/updateDp/{price}/{new_price}")
async def updateDp(
        price:int,
        new_price:int,
        decisionPoints: Annotated[object, Depends(get_decision_points_manager)],
        check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    return decisionPoints.updateDp(price, new_price)


class TradePlanRequest(BaseModel):
    date: date

class TradePlanUpdate(BaseModel):
    plan: str
@router.get("/api/tradePlan")
def get_plan(
        date: date,
        db_helper: Annotated[object, Depends(get_db_manager)],
) -> Dict[str, str]:
    try:
        date = date.strftime("%Y-%m-%d")
        return db_helper.get_plan(date)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/api/tradePlan", response_model=PlanSchema)
def create_or_update_plan(
        plan: PlanSchema,
        db_helper: Annotated[object, Depends(get_db_manager)],
        check_roles: None = Depends(role_checker(["ROLE_ADMIN"]))):
    try:
        db_plan = db_helper.add_or_update_plan(plan)  # Pass the db session
        return db_plan
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/api/fetchHistoricalData/{tsym}")
def fetch_historical_data(
        tsym: str,
        dhan_helper: Annotated[object, Depends(get_dhan_helper)],
        dhan_api: Annotated[object, Depends(get_dhan_api)],
        shoonya_api: Annotated[object, Depends(get_shoonya_api)],

) -> List[Dict[str, Any]]:
    # Get the token for the given symbol
    print(f"Fetching historical data for symbol {tsym}")
    token = dhan_helper.get_token(tsym)

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



# @router.get("/api/fetchHistoricalData/{tsym}")
# def fetch_historical_data(
#         tsym: str,
#         dhan_helper: Annotated[object, Depends(get_dhan_helper)],
#         dhan_api: Annotated[object, Depends(get_dhan_api)],
#
# ) -> List[Dict[str, Any]]:
#     # Get the token for the given symbol
#     print(f"Fetching historical data for symbol {tsym}")
#     token = dhan_helper.get_token(tsym)
#
#     # Calculate the start time (1 week ago, beginning of day)
#     starttime = int(
#         (datetime.now(timezone.utc) - timedelta(weeks=1))
#         .replace(hour=0, minute=0, second=0, microsecond=0)
#         .timestamp()
#     )
#
#     starttime = (date.today() - timedelta(days = 7)).strftime('%Y-%m-%d')
#     endtime = date.today().strftime('%Y-%m-%d')
#
#     # Get the time price series data
#     # res = shoonya_api. get_time_price_series("NFO", str(token), str(starttime), None, "3")
#     idx = 'FUTIDX' if 'FUT' in tsym else 'OPTIDX'
#     res = dhan_api.intraday_minute_data(str(token), 'NSE_FNO', idx, starttime, endtime , 1)
#     res_3m = convert_1m_to_3m(res)
#     return res_3m.to_dict('records')
#     # Convert result to list of dicts (reversed, like in Java)
#     # data_list: List[Dict[str, Any]] = []str(starttime)
#     # if res ==  None:
#     #     return []
#     # for obj in reversed(res):
#     #     data_map = {
#     #         "into": obj.get("into"),
#     #         "stat": obj.get("stat"),
#     #         "ssboe": obj.get("ssboe"),
#     #         "intvwap": obj.get("intvwap"),
#     #         "intoi": obj.get("intoi"),
#     #         "intc": obj.get("intc"),
#     #         "intv": obj.get("intv"),
#     #         "v": obj.get("v"),
#     #         "inth": obj.get("inth"),
#     #         "oi": obj.get("oi"),
#     #         "time": obj.get("time"),
#     #         "intl": obj.get("intl"),
#     #     }
#     #     data_list.append(data_map)
#     # data_list.sort(key=lambda x: x['ssboe'])
#     #
#     # seen_ssboe = set()
#     # filtered_data_list = []
#     #
#     # for entry in data_list:
#     #     ssboe_value = entry.get("ssboe")
#     #     if ssboe_value not in seen_ssboe:
#     #         filtered_data_list.append(entry)
#     #         seen_ssboe.add(ssboe_value)
#
#     return filtered_data_list
#
#
# def convert_1m_to_3m(data):
#     """
#     Convert 1-minute OHLC data to 3-minute OHLC data
#     """
#     # Create DataFrame
#     df = pd.DataFrame(data['data'])
#
#     # Convert timestamp to datetime
#     df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')
#
#     # Set datetime as index
#     df.set_index('datetime', inplace=True)
#
#     # Resample to 3-minute intervals
#     ohlc_3m = df.resample('3min').agg({
#         'open': 'first',  # First open price in the period
#         'high': 'max',  # Highest price in the period
#         'low': 'min',  # Lowest price in the period
#         'close': 'last',  # Last close price in the period
#         'timestamp': 'first'  # First timestamp in the period
#     })
#
#     ohlc_3m = ohlc_3m.rename(columns={
#         'open': 'into',
#         'close': 'intc',
#         'high': 'inth',
#         'low': 'intl',
#         'timestamp': 'ssboe'  # keeping timestamp as is, or change if needed
#     })
#
#     # Remove any rows with NaN values
#     ohlc_3m = ohlc_3m.dropna()
#
#     # Convert back to timestamp format
#     ohlc_3m['timestamp'] = ohlc_3m.index.astype('int64') // 10 ** 9
#
#     return ohlc_3m
#
#
