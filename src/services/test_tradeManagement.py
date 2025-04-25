# from Dhan_Tradehull import Tradehull
from datetime import datetime, timedelta

from conf.config import dhan_api, shoonya_api, logger, nifty_fut_token
from conf.websocketService import update_order_feed, send_toast
from models.partialTrade import PartialTrade
from models.DecisionPoints import decisionPoints
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict

from services.riskManagement import riskManagementobj
from utils.dhanHelper import getProductType
# from conf import websocketService
import concurrent.futures
from models.TradeManager import tradeManager
import pandas as pd
from random import randint
from models.candlestickData import candlestickData
ltps = ()

def setLtps(ltps):
    tradeManager.ltps = ltps

order_list = []
def getNewRandomOrderNumber():
    order_number = 0
    try:
        global order_list
        order_number = randint(1000, 2000)
        while order_number in order_list:
            order_number = randint(1000, 2000)
        order_list.append(order_number)
    except Exception as e:
        logger.error(e)
    return order_number
# subscribedTokens = []
#
#
# def subscribe(token):
#     if not token in subscribedTokens:
#         subscribedTokens.append(token);
#         shoonya_api.subscribe("NFO|" + str(token))


def placeSl(pt, token, trade):
    if trade.status != 0:
        return

    if trade.name == 'trade1':
        return
    #TODO: remove it later, just for trailing testing purpose

    # res = shoonya_api.place_order(
    #     "S", trade.prd, trade.exch, trade.tsym,
    #     trade.qty, "STOP_LOSS", trade.slPrice, trade.slPrice + trade.diff
    # )

    logger.info(f"placing sl order for {trade.name} and token {trade.token}")

    # res = dhan_api.Dhan.place_order(security_id=trade.token, exchange_segment="NSE_FNO", transaction_type="SELL",
    #             quantity=trade.qty, order_type="STOP_LOSS", product_type=trade.prd, price=trade.slPrice, trigger_price=trade.slPrice + trade.diff)
    # logger.info(res)
    # Todo: fix order status when rejected

    #TODO: testing
    res = dict()
    res['status'] = 'success'
    res['data'] = dict()
    res['data']['orderId'] = getNewRandomOrderNumber()
    # pass

    if res['status'] != 'failure':
        orderNumber = res['data']['orderId']
        trade.orderNumber = orderNumber
        trade.status = 1
        trade.orderType = "STOP_LOSS"

        logger.info(f"{trade.name} placed sl for a fresh order at price {trade.slPrice} with order number {orderNumber}")
        # logger.debug(trade.__str__())

    else:
        logger.info(f"error in placing sl order {res['remarks']} ")

    tradeManager.updatePartialTrade(trade)
    # logger.info(f"placed sl for a fresh order for {trade.name} with order number {orderNumber}")


def get_sl_by_swing_lows(df, ltp):
    result_lows = []

    for i in range(3, len(df) - 3):  # Skip first 3 and last 3 candles
        current_low = df['low'][i]

        # Check if current low is lower than the 3 left and 3 right neighbors
        if current_low < min(df['low'][i - 3:i]) and current_low < min(df['low'][i + 1:i + 4]):
            result_lows.append(current_low)
    result_lows.sort(reverse=True)
    for result_low in result_lows:
        if result_low < ltp:
            return result_low
    return 0

def manageTrade(ltp, token, pt, trade, current_time):
    if token != trade.token:
            return

    if not tradeManager.isTradeActive(token) or trade.status == 2:
        return

    if trade.name == 'trade1':
        return
    #TODO: remove it later, just for trailing testing purpose

    points = round(ltp - trade.entryPrice, 1)
    targetPoints = trade.targetPoints
    # logger.info(f"points are {points}")
    # todo: find better logic
    try:
        if  trade.targetPoints > 0:
            if points >= 2.0 / 3 * targetPoints and trade.orderType == "STOP_LOSS":
                logger.info(f"{trade.name} modifying sl order from STOP_LOSS to LIMIT")
                # logger.debug(f"modifying trade {trade.__str__()}")
                # ret = dhan_api.Dhan.modify_order(order_id=trade.orderNumber, order_type="LIMIT", leg_name="ENTRY_LEG",
                #                                  quantity=trade.qty, price=trade.targetPoints, trigger_price=0, disclosed_quantity=0, validity='DAY')
                logger.info(f"{trade.name} cancelling sl order {trade.orderNumber} ")
                res = dict()
                res['status'] = 'success'
                res['data'] = dict()
                res['data']['orderId'] = getNewRandomOrderNumber()

                logger.info(f"{trade.name}  modified placed limit order")

                trade.orderType = "LMT"
                # trade.orderNumber = res['data']['orderId']
                logger.info(f"{trade.name} sl order modified from STOP_LOSS to LMT with target {trade.targetPoints}")
            if points <= 1.0 / 3 * targetPoints and trade.orderType == "LMT":
                logger.info("{trade.name} modifying target order from LIMIT to STOP_LOSS")
                # ret = dhan_api.Dhan.modify_order(order_id=trade.orderNumber, order_type="STOP_LOSS", leg_name="ENTRY_LEG",
                #                                  quantity=trade.qty, price=trade.slPrice, trigger_price=trade.slPrice + trade.diff, disclosed_quantity=0, validity='DAY')
                for i in range(0,2):
                    # dhan_api.cancel_order(OrderID=trade.targetOrderNumbers[i])
                    logger.info(f"{trade.name} cancelling limit order {trade.orderNumber} ")

                # res = dhan_api.Dhan.place_order(security_id=trade.token, exchange_segment="NSE_FNO", transaction_type="SELL",
                #                                 quantity=trade.qty, order_type="STOP_LOSS", product_type=trade.prd,
                #                                 price=trade.slPrice, trigger_price=trade.slPrice + trade.diff)
                res = dict()
                res['status'] = 'success'
                res['data'] = dict()
                res['data']['orderId'] = getNewRandomOrderNumber()

                trade.orderType = "STOP_LOSS"
                trade.orderNumber = res['data']['orderId']
                logger.info(f"{trade.name} limit order modified from LIMIT to STOP_LOSS with sl {trade.slPrice}")
                # logger.info(res)
            if ltp < trade.maxSlPrice:
                logger.info(f"{trade.name} limit sl order crossed, exiting all trades with market orders")
                # dhan_api.cancel_all_orders()
                # exit_all_trades(trade)


        # ## trade simulation, put this in sl orders
        # for i in range(0, 2):
        #     if i == 0 and trade.status == 2:
        #         continue

            if ltp >= trade.entryPrice +  trade.targetPoints   :
                logger.info(f"{trade.name} target reached with points {trade.targetPoints}")
                logger.info(f"{trade.name} entry price {trade.entryPrice} exit price {trade.entryPrice +  trade.targetPoints}")
                trade.exitPrice = trade.targetPoints
                trade.status = 2
                # trade.qty = trade.qty - trade.targetQtys[i]
                # trade.targetStatus = trade.targetStatus + 1

        # change it to get swing point before peak, which is msp from your entry point
        # need to get future hmmm, add trade entry time in trade
        # get swing point from before peak price
        if trade.targetPoints == 0:


            try:
            ## (A) keeping sl 3 points below latest swing point
                if current_time.second == 0:
                    df = candlestickData.getTokenDf(token)
                    new_sl_time = candlestickData.getMspLow(nifty_fut_token, trade)

                    # if new_sl_time == None or new_sl_time not in df['time'].values:
                    #     new_sl = trade.slPrice - 3
                    # else:
                    #     new_sl = df[df['time'] == new_sl_time]['low'].values[0]
                    if new_sl_time != None and new_sl_time in df['time'].values:
                        new_sl = df[df['time'] == new_sl_time]['low'].values[0]
                    else:
                        new_sl = trade.slPrice - 3

                    # new_sl = df.loc[new_sl_time, 'low'] -3

                    if new_sl > trade.slPrice + 5:
                        logger.info(f"{trade.name} modifying mazor swing point sl from {trade.slPrice} to {new_sl} at candle {new_sl_time}")
                        trade.slPrice = new_sl
            except Exception as e:
                logger.error(f"error in fetching last swing point at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")


            ## (B) keeping sl 20% below trade peak points
            new_sl = round(ltp * 0.8, 1)
            if new_sl > trade.slPrice + 5:
                logger.info(f"{trade.name} modifying sl from {trade.slPrice} to {new_sl} at 20% below peak  at time {current_time}")
                trade.slPrice = new_sl

            ## (C) modify sl 3 point below crossed dp
            # if trade.optionType == 'CALL':
            #     fut_latest_price = candlestickData.candlestickData[int(nifty_fut_token)][-1]['close']
            # else:
            #     fut_latest_price = candlestickData.candlestickData[int(nifty_fut_token)][-1]['close']
            try:
                if current_time.second == 0:
                    df = candlestickData.getTokenDf(token)
                    fut_latest_price = candlestickData.getLatestPrice(nifty_fut_token)
                    new_sl_time, dp_price = candlestickData.getCrossedDp(fut_latest_price, nifty_fut_token, decisionPoints.decisionPoints, trade)
                    if new_sl_time != None and new_sl_time in df['time'].values:
                        # new_sl = df.loc[new_sl_time, 'low'] # low of last candle which crossed dp
                        new_sl = df[df['time'] == new_sl_time]['low'].values[0]
                        # new_sl = round(ltp - abs(dp_price -  fut_latest_price)/2 - 3, 1) -3 # exact dp
                        if new_sl  > trade.slPrice + 5:
                            logger.info(f"{trade.name} modifying sl to below {dp_price} from {trade.slPrice} to {new_sl} with candle {new_sl_time} at time {current_time}")
                            trade.slPrice = new_sl
            except Exception as e:
                logger.error(f"error in getting price below dp at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")


        if ltp <= trade.slPrice:
            if trade.slPrice > trade.entryPrice:
                logger.info(f"{trade.name} entry price {trade.entryPrice} exit price {trade.slPrice}")
                logger.info(f"{trade.name} trade trailing ends with points {round(trade.slPrice - trade.entryPrice, 1)}")
            else:
                logger.info(f"{trade.name} sl of {trade.entryPrice - trade.slPrice} points reached at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
            trade.status = 2
    except Exception as e:
        logger.error(f"error in managing trade at time {current_time} {e}")

    tradeManager.updatePartialTrade(trade)
    if trade.status == 2 :
        logger.info("trade over")
        tradeManager.removeTrade(trade.token)

def exit_all_trades(trade):
    try:
        dhan_api.Dhan.place_order(
        security_id=trade.token,
        exchange_segment="NSE_FNO",
        transaction_type="SELL",
        quantity=trade.qty,
        order_type="MARKET",
        product_type=trade.prd,
        price=0
        )
    except Exception as e:
        logger.error(f"error in exiting all trades {e}")

def manageOptionSl(token, ltp, current_time):

    if not tradeManager.isTradeActive(token):
        logger.debug("trade status false or current token is not of current trade")
        return

    trades = tradeManager.getTrades(token)

    with ThreadPoolExecutor(max_workers=len(trades)) as executor:
        futures = {executor.submit(placeSl, pt, token, partialTrade): pt for pt, partialTrade in trades.items()}
        for future in as_completed(futures):
            pt = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error in placing SL for {pt}: {e}")

    # trades = tradeManager.getTrades(token)

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(manageTrade, ltp, token, pt, partialTrade, current_time): pt for pt, partialTrade in
                   trades.items()}
        for future in as_completed(futures):
            pt = futures[future]
            try:
                future.result()
            except Exception as e:
                logger.error(f"Error in managing trade for {pt}: {e}")




def createTrade(token, order_update):
    try:
        #TODO: testing
        # tradeManager.ltps[nifty_fut_token] = 22950

        future_ltp = tradeManager.ltps[nifty_fut_token]

        qty = order_update['quantity']
        entryPrice = order_update['tradedPrice']
        tsym = order_update['displayName']
        product = order_update['product']
        prd = getProductType(product)
        optionType = tsym.split(' ')[-1]

        slPrice = entryPrice - 10  # TODO: fetch from config
        maxSlPrice = entryPrice - 12
        minLotSize = 75

        half = qty // 2
        qty1 = (half // minLotSize) * minLotSize
        qty2 = qty - qty1

        #TODO: changfe it
        target1, target2 = 25, 25
        trade1 = PartialTrade(
            name="trade1", status=0, qty=qty1, entryPrice=entryPrice, slPrice=slPrice, maxSlPrice=maxSlPrice,
            targetPoints=target1, orderType="STOP_LOSS", prd=prd, exch="NSE_NFO", tsym=tsym,
            diff=0.2, token=token, optionType=optionType
        )

        trade2 = PartialTrade(
            name="trade2", status=0, qty=qty2, entryPrice=entryPrice, slPrice=slPrice, maxSlPrice=maxSlPrice,
            targetPoints=target2, orderType="STOP_LOSS", prd=prd, exch="NSE_NFO", tsym=tsym,
            diff=0.2, token=token, optionType=optionType
        )

        tradeManager.addTrade(token, "trade1", trade1)
        tradeManager.addTrade(token, "trade2", trade2)

        # trade = tradeManager.trade
        # trade.targetQtys = [qty1, qty2]
        # trade.targetPrices = decisionPoints.getTargetPrices(future_ltp, tradeManager.trade )
        # trade.slPrice = slPrice
        # trade.maxSlPrice = maxSlPrice
        # trade.prd = prd
        # trade.entryPrice = order_update['tradedPrice']
        # trade.status = 0 # make it elligible for placeSl function
        # logger.info(trade.__str__())
    except Exception as e:
        logger.error(f"Error in creating trade  {e}")

def handle_buy_order(token, order_update):
    try:
        if tradeManager.trade == None:
          #todo: if trade doesnt exist already
            tsym = dhan_api.get_trading_symbol(int(token))
            optionType = tsym.split(' ')[-1]
            trade = PartialTrade(
                name="test",  token=token, status=-1, qty=riskManagementobj.qty, entryPrice=order_update['tradedPrice'],
                orderType="LIMIT",  exch="NSE_NFO", tsym=tsym, diff=0.2, optionType=optionType, bof=False
            )
            tradeManager.setTrade(trade)
            shoonya_api.subscribe("NFO|" + str(token))

        if tradeManager.trade.status == -1:
            logger.info(f"starting a fresh trade at {datetime.now()}");
            createTrade(token, order_update)
            decisionPoints.updateDecisionPoints(tradeManager.ltps[nifty_fut_token], order_update['optType'])
    except Exception as e:
        logger.error(f"Error in handling buy order {e}")
    #
    # trades = tradeManager.getTrade(token)
    #
    # with ThreadPoolExecutor(max_workers=len(trades)) as executor:
    #     futures = {executor.submit(placeSl, pt, token, partialTrade): pt for pt, partialTrade in trades.items()}
    #     for future in as_completed(futures):
    #         pt = futures[future]
    #         try:
    #             future.result()
    #         except Exception as e:
    #             logger.error(f"Error in placing SL for {pt}: {e}")


def updateSl(token, new_sl_price, order_update):
    trade = tradeManager.token
    old_sl_price = trade.slPrice
    trade.slPrice = new_sl_price
    logger.info(f"old sl price is {old_sl_price} new sl price is {new_sl_price}")

    return

    old_sl_price = trades["t1"].slPrice
    executor = None
    if old_sl_price != new_sl_price:
        logger.info(f"modifying all remaining sl from {old_sl_price} to {new_sl_price}")
        try:
            executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(trades))
            futures = []
            for pt, partial_trade in trades.items():
                partial_trade.slPrice = new_sl_price
                try:
                    if partial_trade.status == 1:
                        if partial_trade.orderNumber == order_update["orderNo"]:
                            logger.info("Sl changed manually for trade %s", partial_trade.name)
                        else:
                            logger.info("modifying sl for %s", partial_trade.name)
                            future = executor.submit(
                                dhan_api.Dhan.modify_order,
                                order_id=partial_trade.orderNumber,
                                order_type="STOP_LOSS",
                                leg_name="ENTRY_LEG",
                                quantity=partial_trade.qty,
                                price=partial_trade.slPrice,
                                trigger_price=partial_trade.slPrice + 0.2,
                                disclosed_quantity=0,
                                validity='DAY'
                            )
                            futures.append(future)
                except Exception as e:
                    logger.error(f"Exception occurred during modifying order for trade {partial_trade.name}: {e}")

        finally:
            if executor:
                executor.shutdown(wait=True)
                for future in futures:
                    try:
                        future.result()  # Ensure any raised exceptions are caught
                    except Exception as e:
                        logger.error(f"Exception occurred during modifying order: {e}")
    else:
        logger.info(f"new sl order has same price {old_sl_price}")

def handle_sell_order(token, order_update):
    if order_update['txnType'] == 'S' and order_update['status'] == 'Modified' and order_update['orderType'] == 'SL':
        logger.info(f"new manual sl order received for token {token}")
        newSlPrice = order_update['price']
        logger.info(f"new sl price is {newSlPrice}")
        # updateSl(token, newSlPrice, order_update)

    elif order_update['txnType'].upper() == 'S' and order_update['status'].upper() == 'TRADED' and order_update['orderType'].upper() == 'LMT':
        logger.info(f"sell limit order completed")
        logger.info(f"{order_update}")

        trade = tradeManager.trade

        for i in range(0,2):
            if order_update['orderNo'] == trade.targetOrderNumbers[i] :
                trade.exitPrice[i] = order_update['tradedPrice']
                # trade.status = trade.status + 1
                trade.targetStatus = trade.targetStatus + 1
                logger.debug(f"{i+1}th target completed {trade.__str__()}")

        if order_update['orderNo'] == trade.orderNumber:
            logger.info('sl got hit')
            trade.status = 3
            trade.exitPrice[i] = order_update['tradedPrice']

        if trade.status == 3 or trade.targetStatus == 3: # trades are completed
            logger.info(f"all active trades for token {token} completed")
            logger.info(f"All trades completed, final Trade is \n {tradeManager.trade}")
            tradeManager.removeTrade()
            logger.info(f"set trade to {tradeManager.trade}")
            logger.info("checking killswitch condition")
            # update last trade time
            riskManagementobj.sanityCheck()


def updateOpenOrders():
    orders =  dhan_api.Dhan.get_order_list()['data']
    openOrders = []
    for order in orders:
        if order['orderStatus'].upper() == 'PENDING':
            openOrders.append(order)
    update_order_feed(openOrders)


def handle_order(order_update: dict):
    token = order_update['securityId']

    # if order_update['status'] == 'Cancelled' and order_update['txnType'] == 'B':
    #     handle_buy_order(token, order_update)
    #     tradeManager.trade = None

    if order_update['status'] == 'Traded' and order_update['txnType'] == 'B':
        handle_buy_order(token, order_update)

    if order_update['txnType']  == 'S':
        handle_sell_order(token, order_update)

def on_order_update(order_data: dict):
    """Optional callback function to process order data"""
    print("new order received")
    order_update = order_data.get("Data", {})
    logger.info(order_update)

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(handle_order, order_update)
        executor.submit(updateOpenOrders)




def updateTargets(targets: Dict[str, float]):

    logger.info("targets are {}, {}, {}".format(targets.get("t1"), targets.get("t2"),
                                                targets.get("t3")))

    if not tradeManager.isTradeActive():
        logger.info("trade is not active")
        send_toast("Targets Update request", "Trade is not active")
        return {"message": "Trade is not active"}
    old_targets = tradeManager.trade.targetPointss
    try:
        trade = tradeManager.trade
        trade.targetPointss = [targets["t1"], targets["t2"]]

        if trade.orderType == "LMT":
            for i in range(0,2):
                logger.info(f" trade {i+1} modifying limit order price from {old_targets[i]} to {trade.targetPointss[i]} ")
                # ret = dhan_api.Dhan.modify_order(order_id=trade.targetOrderNumbers[i], order_type="LIMIT", quantity=trade.targetQtys[i],
                #                                  price=trade.targetPointss[i])
                ret = dict()
                ret['status'] = 'success'
                # logger.info(ret)
    except Exception as e:
        logger.error(f"error in updating target for the trades {e}")

    # trade = tradeManager.trade
    #
    # for partial_trades in trades.values():
    #     for trade in partial_trades.values():
    #         entry_price = trade.entry_price
    #         initial_target_price = trade.target_price
    #
    #         # update target based on name
    #         if trade.name == "t1":
    #             trade.set_target_price(targets.get("t1") + entry_price)
    #         if trade.name == "t2":
    #             trade.set_target_price(targets.get("t2") + entry_price)
    #         if trade.name == "t3":
    #             trade.set_target_price(targets.get("t3") + entry_price)
    #
    #         # change limit order price if already in place
    #         if trade.order_type == "LMT":
    #             ret = dhan_api.Dhan.modify_order(order_id=trade.orderNumber, order_type="LIMIT", quantity=trade.qty,
    #                                              price=trade.targetPoints)
    #
    #             logger.info(
    #                 "LMT order of trade {} got modified from {} to {}".format(trade.name, initial_target_price,
    #                                                                           trade.target_price))
    #             logger.info(ret)
    # websocketService.send_toast("Targets Update request", "Targets Updated")
    return 0


# def run( time, expiry, tsym , dps = [] ):
#
#     try:
#
#         # tsym = "NIFTY 27 MAR 23650 CALL"
#         optionType = tsym.split(' ')[-1]
#
#         decisionPoints.decisionPoints = []
#         # add decision points
#         month = expiry.strftime('%m').zfill(2)
#         day = expiry.strftime('%d').zfill(2)
#
#         for dp in dps:
#             decisionPoints.addDecisionPoint(name=str(dp),price= dp )
#
#
#         fut_token_df = pd.read_csv(f"/home/kushy/PycharmProjects/TradeApp/candleStickData/NIFTY/futureData/2025/{month}/3m/NIFTY_F1.csv")
#         fut_token_df['time'] = pd.to_datetime(fut_token_df['time'], format='%Y-%m-%d %H:%M:%S')
#
#
#         option = 'NIFTY' + expiry.strftime('%d').zfill(2) + expiry.strftime('%b%y').upper() + tsym.split(' ')[-1][0] + tsym.split(' ')[3]
#         token_df = pd.read_csv(f"/home/kushy/PycharmProjects/TradeApp/candleStickData/NIFTY/optionData/2025/{month}/{day}/3m/{option}.csv")
#         token_df['time'] = pd.to_datetime(token_df['time'], format='%Y-%m-%d %H:%M:%S')
#
#         df = token_df[(token_df.time >= time) & (token_df.time.dt.date == time.date())]
#         fut_df = fut_token_df[ (fut_token_df.time >= time) & (fut_token_df.time.dt.date == time.date())]
#
#
#         entryPrice = df.iloc[0]['close']
#         target1, target2 = 25, 0
#         token = "48695"
#
#         trade1 = PartialTrade(
#             name="trade1", status=0, qty=150, entryPrice=entryPrice, slPrice=entryPrice-5, maxSlPrice=entryPrice-7,
#             targetPoints= target1, orderType="STOP_LOSS", prd='INTRADAY', exch="NSE_NFO", tsym=tsym,
#             diff=0.2, token=token, optionType=optionType, startTime=time
#         )
#
#         trade2 = PartialTrade(
#             name='trade2', status=0, qty=75, entryPrice=entryPrice, slPrice=entryPrice-5, maxSlPrice=entryPrice-7,
#             targetPoints=target2, orderType="STOP_LOSS", prd='INTRADAY', exch="NSE_NFO", tsym=tsym,
#             diff=0.2, token=token, optionType=optionType, startTime=time
#         )
#
#         tradeManager.addTrade(token, trade1)
#         tradeManager.addTrade(token, trade2)
#
#
#         logger.info(f"starting trade with entry price {entryPrice}")
#
#
#         for idx, close_price in enumerate(df['close']):
#             current_option_df = df.iloc[:idx + 1].copy()
#             candlestickData.candlestickData[token] = current_option_df
#             current_time = current_option_df.iloc[-1]['time']
#             candlestickData.candlestickData[nifty_fut_token] = fut_df[fut_df['time'] <= current_time].copy()
#             if current_time == datetime(2025, 3, 28, 9, 36):
#                 pass
#             manageOptionSl(token, float(close_price), current_time)
#
#         trades = tradeManager.getTrades(token)
#         trade2 = trades.get('trade2')
#
#
#         if trade2.status != 2:
#             # print("trade is not finished")
#             # print(f"last price is {df.iloc[-1]['close']}")
#             logger.info(f"points are {df.iloc[-1]['close'] - entryPrice }")
#
#             # time.sleep(0.1)
#     except Exception as e:
#         logger.error(e)



def run_feed( time, expiry, tsym , dps = [] ):
    try:
        candlestickData.reset()
        feed_df = pd.read_csv('data/feed/' + time.strftime('%Y-%m-%d') + '.csv')
        feed_df['time'] = pd.to_datetime(feed_df['time'], format='%Y-%m-%dT%H:%M:%S')
        # token = dhan_api.get_security_id(tsym , "NFO")
        # tsym = "NIFTY 27 MAR 23650 CALL"
        optionType = tsym.split(' ')[-1]

        expiry_day = int(tsym.split(' ')[1])
        expiry_month = int(datetime.strptime(tsym.split(' ')[2].title(), '%b').strftime('%m'))
        expiry = datetime(datetime.now().year, expiry_month, expiry_day)
        # add decision points
        # month = expiry.strftime('%m').zfill(2)
        # day = expiry.strftime('%d').zfill(2)

        decisionPoints.decisionPoints = []
        for dp in dps:
            decisionPoints.addDecisionPoint(name=str(dp),price= dp )

        post_entry_df =  feed_df[(feed_df['time'] >= time) & (feed_df['tsym'] == tsym)]
        # post_entry_df_token = feed_df[feed_df['token'] == token]
        post_entry_df_time = feed_df[feed_df['time'] >= time]
        entryPrice = post_entry_df.iloc[0]['price']
        target1, target2 = 25, 0
        token = post_entry_df.iloc[0]['token']
        trade1 = PartialTrade(
            name="trade1", status=0, qty=150, entryPrice=entryPrice, slPrice=entryPrice-10, maxSlPrice=entryPrice-7,
            targetPoints= target1, orderType="STOP_LOSS", prd='INTRADAY', exch="NSE_NFO", tsym=tsym,
            diff=0.2, token=token, optionType=optionType, startTime=time
        )

        trade2 = PartialTrade(
            name='trade2', status=0, qty=75, entryPrice=entryPrice, slPrice=entryPrice-10, maxSlPrice=entryPrice-7,
            targetPoints=target2, orderType="STOP_LOSS", prd='INTRADAY', exch="NSE_NFO", tsym=tsym,
            diff=0.2, token=token, optionType=optionType, startTime=time
        )

        tradeManager.addTrade(token, trade1)
        tradeManager.addTrade(token, trade2)


        logger.info(f"starting trade with entry price {entryPrice}")
        trade_df = feed_df[feed_df['time'] >= time - timedelta(minutes = 1)]

        i = 0
        for index, row in trade_df.iterrows():
            tt = row['time']
            token = row['token']
            price = row['price']
            feed_data = {'ltp': price, 'ft': tt.timestamp() }
            candlestickData.updateTickData(token, feed_data)
            manageOptionSl(token, price, tt)

            if i%3000 == 0: #
                pass
            i += 1

            if not tradeManager.isTradeActive():
                break
        logger.info("for loop ended")
    except Exception as e:
        logger.error(e)


