from logging import raiseExceptions

from conf.config import dhan_api, shoonya_api, logger, order_folder, nifty_fut_token
from models.partialTrade import PartialTrade
from services.riskManagement import riskManagementobj
from conf import websocketService
from models.DecisionPoints import decisionPoints
from conf.shoonyaWebsocket import ltps
from models.TradeManager import tradeManager
from datetime import datetime

def buyOrder(token, order_type, price, bof):

    try:

        # return if trade is already active
        if tradeManager.isTradeActive():
            websocketService.send_toast("Wrong trade", "Another trade already open")
            return

        tsym = dhan_api.get_trading_symbol(int(token))
        optionType = tsym.split(' ')[-1]

        triggerPrice = 0.0
        if order_type == "STOP_LOSS":
            triggerPrice = price - 0.2

        if order_type == "SL":
            logger.info(f"sl order with sl as {price} and buy price at {price + 4}")
            price = price + 8

        # return if last trade was within 5 m of closing of previous trade
        minutes_left = riskManagementobj.overTrading()
        if minutes_left:
            websocketService.send_toast("overtrading", f"wait for {minutes_left} minutes")
            logger.info(f"overtrading, wait for {minutes_left} minutes")
            return

        # 2 trades before 12 and 2 after
        tradeCount = riskManagementobj.tradeCount
        if tradeCount >=3 and datetime.now() <= datetime.now().replace(hour=12, minute=0, second=0, microsecond=0):
            websocketService.send_toast("overtrading", f"{tradeCount} trades done before 12 PM")
            logger.info(f"{tradeCount} trades done before 12 PM")
            return


        # TODO: testing
        # ltps[nifty_fut_token] = 22950


        if order_type == "LIMIT":
            fut_ltp = ltps[nifty_fut_token]
            if not decisionPoints.checkTradeValidity(fut_ltp, optionType):
                websocketService.send_toast("Wrong trade", "Price not near any DP")
                logger.info(f"Wrong trade, Price not near any DP or DP already traded")
                return


        if tradeManager.ltps[token] < price - 5 and order_type == "LIMIT":
            websocketService.send_toast("Wrong trade or option", "Price too high")
            logger.info("Wrong ATM option or Price too high than ltp")
            return

        if tradeManager.ltps[token] < price and order_type == "LIMIT":
            logger.info("higher price than ltp, using ltp as price ")
            price = tradeManager.ltps[token] + 0.5

        qty = riskManagementobj.getQty(price)

        res = dhan_api.Dhan.place_order(security_id=token, exchange_segment="NSE_FNO", transaction_type="BUY",
                    quantity=qty, order_type='LIMIT', product_type="INTRADAY", price=price, trigger_price=triggerPrice)

        logger.info(f"Manual buy order status")
        logger.info(res)

        # TODO: testing
        # res['status'] = 'success'


        if res['status'] == 'success':
            # trade = PartialTrade(
            #     name="test",  token=token, status=-1, qty=riskManagementobj.qty, entryPrice=price,
            #     orderType="LIMIT",  exch="NSE_NFO", tsym=tsym, diff=0.2, optionType=optionType, bof=bof, starttime=datetime.now()
            # )
            # logger.info(trade.__str__())
            # tradeManager.setTrade(trade)
            shoonya_api.subscribe("NFO|" + str(token))

        if res['status'] == 'failure':
            websocketService.send_toast("Order failed", res['remarks']['error_message'])

    except Exception as e:
        logger.error(f"error in placing order {e}")
        websocketService.send_toast("Order failed", f"{e}")
        # if 'status' in res and res['status'] == 'failure':
        #     websocketService.send_toast("Order failed", f"{e}")
        raiseExceptions(e)




def modifyActiveOrder(orderId, newPrice):
    # token = "38614"
    # trade1 = PartialTrade(
    #     name="trade1", status=0, qty=100, entryPrice=100, slPrice=90, maxSlPrice=90,
    #     targetPoints=110, orderType="STOP_LOSS", prd='I', exch="NSE_NFO", tsym="NIFTY 08 MAY 24500 PUT",
    #     diff=0.2, token=token, optionType="PUT"
    # )
    #
    # trade2 = PartialTrade(
    #     name="trade2", status=0, qty=100, entryPrice=100, slPrice=90, maxSlPrice=90,
    #     targetPoints=110, orderType="STOP_LOSS", prd='I', exch="NSE_NFO", tsym="NIFTY 08 MAY 24500 PUT",
    #     diff=0.2, token=token, optionType="PUT"
    # )
    #
    # tradeManager.addTrade(token,  trade1)
    # tradeManager.addTrade(token, trade2)

    partialTrades = None
    for token in tradeManager.trades:
        partialTrades = tradeManager.getTrades(token)

    if partialTrades is None:
        logger.info(f"no active trades, probably a limit order")
        try:
            order = dhan_api.get_order_detail(orderId)
            if order["orderType"] == "LIMIT":
                logger.info(f"changing limit order of orderId {orderId} to price {newPrice} ")
                res = dhan_api.Dhan.modify_order(order_id=orderId, order_type="LIMIT", leg_name="ENTRY_LEG",quantity=order["quantity"],
                                           price=newPrice, trigger_price=0, disclosed_quantity=0, validity='DAY')
                logger.info(f"{res}")
                # tradeManager['entryPrice'] = newPrice
        except Exception as e:
            logger.error("failed to modify order with error {}".format(e))

    else:
        trade_type = partialTrades['trade1'].orderType
        if trade_type == "STOP_LOSS":
            try:
                for trade in partialTrades.values():
                    logger.info(f"changing SL price of {trade.name} from {trade.slPrice} to {newPrice}")
                    res = dhan_api.Dhan.modify_order(order_id=trade.orderNumber, order_type="STOP_LOSS", leg_name="ENTRY_LEG",
                                               quantity=trade.qty,
                                               price=newPrice, trigger_price=newPrice +  0.5,
                                               disclosed_quantity=0, validity='DAY')
                    logger.info(res)
            except Exception as e:
                logger.error(f"error in modifying active SL order {e} ")



def modifyActiveOrderOld(orderId, newPrice):

    order = dhan_api.get_order_detail(orderId)

    if order["orderType"] == "LIMIT":
        try:
            dhan_api.Dhan.modify_order(order_id=orderId, order_type="LIMIT", leg_name="ENTRY_LEG",quantity=order["quantity"],
                                       price=newPrice, trigger_price=0, disclosed_quantity=0, validity='DAY')
        except Exception as e:
            logger.error("failed to modify order with error {}".format(e))
        # else:
        #     tradeManager['entryPrice'] = newPrice

    #TODO: update tradeManager on SL trade
    type_modifier = -1 if order["transactionType"] == "BUY" else 1
    if order["orderType"] == "STOP_LOSS":
        # shoonyaHelper.modifyOrder(order["exch"], order["tsym"], norenordno, order["qty"], "SL-LMT", newPrice, newPrice + 0.2 * type_modifier)

            # ret = dhan_api.Dhan.modify_order(order_id=trade.orderNumber, order_type="LIMIT", leg_name="ENTRY_LEG",
            #                                  quantity=trade.qty, price=trade.targetPrice, trigger_price=0, disclosed_quantity=0, validity='DAY')

        dhan_api.Dhan.modify_order(order_id=orderId, order_type="STOP_LOSS", leg_name="ENTRY_LEG",quantity=order["quantity"],
                                   price=newPrice, trigger_price=newPrice + type_modifier * 0.2, disclosed_quantity=0, validity='DAY')


def cancelOrder(orderId):
    try:
        dhan_api.cancel_order(orderId)
    except Exception as e:
        logger.error("failed to cancel order with error {}".format(e))
    # else:
    #     tradeManager.trade = None



def getOrderBook():
    orders = dhan_api.get_orderbook()
    try:
        validOrders = orders[orders["orderStatus"] == "TRADED"].reset_index(drop=True)
        validOrders = validOrders[['orderId', 'transactionType', 'orderType', 'tradingSymbol', 'exchangeTime', 'filledQty', 'averageTradedPrice']]
        orderFile = order_folder + str(datetime.now().date()) + '.csv'
        validOrders.to_csv(orderFile, index=False)
    except Exception as e:
        logger.error(f"error in downloading orderData {e}")

