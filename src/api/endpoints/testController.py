from fastapi import APIRouter, BackgroundTasks
from conf.config import dhan_api, riskManagement
from conf.logging_config import logger
from conf.config import tradeManagement, tradeManager, orderManagement

# from services.test_tradeManagement import  run_feed, run
# from services.postMarketAnalysis import trailTrades

from conf.config import orderManagement
from pydantic import BaseModel
from conf import websocketService
import random
from datetime import datetime
from typing import List

from models.partialTrade import PartialTrade
router = APIRouter()
from models.DecisionPoints import decisionPoints

@router.get("/api/placeOrder")
async def pnl():
    return dhan_api.order_placement(tradingsymbol="NIFTY 13 MAR 22150 PUT", exchange="NFO", quantity=150, price=0, trigger_price=0, order_type="MARKET", transaction_type="BUY",trade_type="MIS",  )


@router.get("/api/test")
async def brokerage():
    riskManagement.lockScreen()
    return 0



class QuoteResponse(BaseModel):
    quote: str


@router.get("/api/quote", response_model=QuoteResponse)
async def quote():
    return QuoteResponse(quote="just fucking follow the rules")

@router.get("/api/testTrade")
async def test_order_update():
    trade1 = PartialTrade(
        name="trade1", status=0, qty=75, entryPrice=138.5, slPrice=133.5, maxSlPrice=129.5,
        targetPoints=15, orderType="STOP_LOSS", prd="INTRADAY", exch="NSE_NFO", tsym="NIFTY 27 MAR 23750 PUT",
        diff=0.2, token="53847", optionType="PUT"
    )


    trade2 = PartialTrade(
        name="trade2", status=0, qty=75, entryPrice=138.5, slPrice=133.5, maxSlPrice=129.5,
        targetPoints=15, orderType="STOP_LOSS", prd="INTRADAY", exch="NSE_NFO", tsym="NIFTY 27 MAR 23750 PUT",
        diff=0.2, token="53847", optionType="PUT"
    )
    trade1.status = 1
    trade1.orderNumber = '102250326300827'
    trade2.status = 1
    trade2.orderNumber = '102250326300826'


    tradeManager.addTrade("53847", trade1)
    tradeManager.addTrade("53847", trade2)


@router.get("/api/testOrder")
async def test_order_update():
    order_update = {'exchange': 'NSE', 'segment': 'D', 'source': 'P', 'securityId': '53847', 'clientId': '1103209581', 'exchOrderNo': '1600000085011333', 'orderNo': '102250326300826', 'product': 'I', 'txnType': 'S', 'orderType': 'LMT', 'validity': 'DAY', 'quantity': 75, 'tradedQty': 75, 'price': 133.5, 'tradedPrice': 133.55, 'avgTradedPrice': 133.55, 'offMktFlag': '0', 'orderDateTime': '2025-03-26 11:11:19', 'exchOrderTime': '2025-03-26 11:13:00', 'lastUpdatedTime': '2025-03-26 11:13:00', 'remarks': ' ', 'mktType': 'NL', 'reasonDescription': 'TRADE CONFIRMED', 'legNo': 1, 'instrument': 'OPTIDX', 'symbol': 'NIFTY-Mar2025-2', 'productName': 'INTRADAY', 'status': 'Traded', 'lotSize': 75, 'strikePrice': 23750, 'expiryDate': '2025-03-27', 'optType': 'PE', 'displayName': 'NIFTY 27 MAR 23750 PUT', 'isin': 'NA', 'series': 'XX', 'goodTillDaysDate': '2025-03-26', 'refLtp': 139, 'tickSize': 0.05, 'algoId': '0', 'multiplier': 1, 'correlationId': '1103209581-1742967679712'}

    order = {"Data" : order_update }
    tradeManagement.on_order_update(order)

    order_update = {'exchange': 'NSE', 'segment': 'D', 'source': 'P', 'securityId': '53847', 'clientId': '1103209581', 'exchOrderNo': '1600000085011333', 'orderNo': '102250326300827', 'product': 'I', 'txnType': 'S', 'orderType': 'LMT', 'validity': 'DAY', 'quantity': 75, 'tradedQty': 75, 'price': 133.5, 'tradedPrice': 133.55, 'avgTradedPrice': 133.55, 'offMktFlag': '0', 'orderDateTime': '2025-03-26 11:11:19', 'exchOrderTime': '2025-03-26 11:13:00', 'lastUpdatedTime': '2025-03-26 11:13:00', 'remarks': ' ', 'mktType': 'NL', 'reasonDescription': 'TRADE CONFIRMED', 'legNo': 1, 'instrument': 'OPTIDX', 'symbol': 'NIFTY-Mar2025-2', 'productName': 'INTRADAY', 'status': 'Traded', 'lotSize': 75, 'strikePrice': 23750, 'expiryDate': '2025-03-27', 'optType': 'PE', 'displayName': 'NIFTY 27 MAR 23750 PUT', 'isin': 'NA', 'series': 'XX', 'goodTillDaysDate': '2025-03-26', 'refLtp': 139, 'tickSize': 0.05, 'algoId': '0', 'multiplier': 1, 'correlationId': '1103209581-1742967679712'}

    order = {"Data" : order_update }
    tradeManagement.on_order_update(order)

@router.get("/api/testFeed")
async def test_order_update():
    # price 130 : target
    tradeManagement.manageOptionSl('50179', 125)
    tradeManagement.manageOptionSl('50179', 154)
    tradeManagement.manageOptionSl('50179', 140)

    tradeManagement.manageOptionSl('50179', 165)

@router.get("/api/modifyOrder")
async def modifyOrder():
    # ret = dhan_api.Dhan.modify_order(order_id="12250307294127", order_type="LIMIT", quantity=75,
    #                                  price=101)
    ret = dhan_api.Dhan.modify_order( order_id=22250307395227, order_type="LIMIT", leg_name="ENTRY_LEG",  quantity=75,
                                      price=160, trigger_price=0, disclosed_quantity=0, validity='DAY')

    print(ret)

@router.get("/api/getGreek")
async def getGreek():
    ret = dhan_api.get_option_greek(22500, 0, "NIFTY", 7, "delta", "CE")
    print(ret)

    # def get_option_greek(self, strike: int, expiry: int, asset: str, interest_rate: float, flag: str, scrip_type: str):


@router.get("/api/sampleFeed")
async def getGreek():
    epoch = int(datetime.now().timestamp())
    websocketService.send_price_feed("45467", epoch, 100 * random.random())
    websocketService.send_price_feed("45475", epoch, 100 * random.random())


@router.get("/api/toast")
async def getGreek():
    websocketService.send_toast("hello", "world")

@router.post("/api/addDp/{price}/{name}")
async def getGreek(price:int, name:str):
    decisionPoints.addDecisionPoint(price, name)

@router.post("/api/testDp/{price}/{type}")
async def getGreek(price:int, type:str):
    decisionPoints.updateDecisionPoints(price, type)


@router.get("/api/orderUpdate")
async def getGreek():
    tradeManagement.updateOpenOrders()

@router.get("/api/sanityCheck")
async def sanityCheck():
    riskManagement.sanityCheck()

@router.get("/api/getTsym/{token}")
async def getTsym(token:int):
    tsym = dhan_api.get_trading_symbol(token)
    logger.info(tsym)


class TradeRequest(BaseModel):
    time: str
    expiry: str
    tsym: str
    dps: List[float]
    def to_datetime(self):
        self.time = datetime.fromisoformat(self.time)
        self.expiry = datetime.fromisoformat(self.expiry)

# @router.post("/api/tradeCheck")
# async def tradeCheck( background_tasks: BackgroundTasks, trade: TradeRequest ):
#     trade.to_datetime()
#     # token = trade.token
#
#     time = trade.time
#     expiry = trade.expiry
#     dps = trade.dps
#
#     # tsym = 'NIFTY ' +  expiry.strftime('%d %b ').upper() + str(strike_price) +  ' ' +optionType
#     tsym = trade.tsym
#     # run_feed(time, expiry, tsym, dps)
#     background_tasks.add_task(run_feed,  time, expiry , tsym, dps)
#
#     return {"message": "Trade started, not waiting for completion"}
#     # run()

# @router.post("/api/tradeCheckOld")
# async def tradeCheck( background_tasks: BackgroundTasks, trade: TradeRequest ):
#     trade.to_datetime()
#     # token = trade.token
#
#     time = trade.time
#     expiry = trade.expiry
#     dps = trade.dps
#
#     # tsym = 'NIFTY ' +  expiry.strftime('%d %b ').upper() + str(strike_price) +  ' ' +optionType
#     tsym = trade.tsym
#     run(time, expiry, tsym, dps)
    # background_tasks.add_task(run,  time, expiry , tsym, dps)

    # return {"message": "Trade started, not waiting for completion"}

# @router.get("/api/tradeCheck")
# async def tradeCheck( background_tasks: BackgroundTasks, trade: TradeRequest ):
#     price = 165
#     strike_price = 22300
#     optionType = ' PUT'
#
#     time = datetime(2025, 3, 3, 9, 42)
#     expiry = datetime(2025, 3, 6, 0, 0)
#     dps = [22360, 22300, 22200, 22100]
#
#     tsym = 'NIFTY ' +  expiry.strftime('%d %b ').upper() + str(strike_price) + optionType
#
#     background_tasks.add_task(run, price, time, expiry , tsym, dps)
#
#     return {"message": "Trade started, not waiting for completion"}

# @router.get("/api/setTargets")
# async def setTargets():
#     targets = {'t1':100, 't2':100, 't3':30}
#     tradeManagement.updateTargets(targets)
#
# @router.get("/api/modifySl")
# async def setTargets():
#     orderManagement.modifyActiveOrder(12, 123);

@router.post("/api/cancelTest/{orderNumber}")
async def cancelTest(orderNumber:int):
    tradeManagement.cancel_order_and_confirm(orderNumber)

# @router.post("/api/trailTest/{days}")
# async def trailTest(days:int):
#     trailTrades(days)

@router.get("/api/getBrokerage")
async def getBrokerage():
    history = dhan_api.Dhan.get_trade_history('2025-05-27','2025-05-29', 0)
    print(history)



