# from Dhan_Tradehull import Tradehull
from datetime import datetime

from conf import websocketService
# from conf.config import     position_folder
from conf.logging_config import logger
from conf.websocketService import update_order_feed, send_toast
from models.partialTrade import PartialTrade
from concurrent.futures import ThreadPoolExecutor, as_completed

# from services.orderManagement import getOrderBook
# from conf.config import riskManagementobj
#
# from conf.config import dhanHelper
# from conf import websocketService
import concurrent.futures
# from models.TradeManager import tradeManager
from models.candlestickData import candlestickData
import time
import pandas as pd
import threading

class TradeManagement:
    def __init__(self, config, dhan_api, shoonya_api,  tradeManager, nifty_fut_token, riskManagementobj, dhanHelper, decisionPoints , misc):
        self.function_lock = threading.Lock()
        self.config = config
        self.tradeManager = tradeManager
        self.dhan_api = dhan_api
        self.shoonya_api = shoonya_api
        self.nifty_fut_token = nifty_fut_token
        self.riskManagementobj = riskManagementobj
        self.dhanHelper = dhanHelper
        self.decisionPoints = decisionPoints
        self.misc = misc
        
    #
    # def setLtps(self, ltps):
    #     self.tradeManager.ltps = ltps
    # # subscribedTokens = []
    #
    #
    # def subscribe(token):
    #     if not token in subscribedTokens:
    #         subscribedTokens.append(token);
    #         self.shoonya_api.subscribe("NFO|" + str(token))


    def placeSl(self, trade:PartialTrade):
        if trade.status != 0:
            return

        # res = self.shoonya_api.place_order(
        #     "S", trade.prd, trade.exch, trade.tsym,
        #     trade.qty, "STOP_LOSS", trade.slPrice, trade.slPrice + trade.diff
        # )

        logger.info(f"placing sl order for {trade.name} and token {trade.token}")

        res = self.dhan_api.Dhan.place_order(security_id=trade.token, exchange_segment="NSE_FNO", transaction_type="SELL",
                    quantity=trade.qty, order_type="STOP_LOSS", product_type=trade.prd, price=trade.slPrice - trade.diff, trigger_price=trade.slPrice )
        logger.info(res)
        # Todo: fix order status when rejected

        if res['status'] != 'failure':
            orderNumber = res['data']['orderId']
            trade.orderNumber = orderNumber
            trade.status = 1
            trade.orderType = "STOP_LOSS"

            logger.info(f"placed sl at {trade.slPrice} for a fresh order with order number {orderNumber}")
            logger.info(trade.__str__())

        else:
            logger.error(
                "Placing order: security_id={}, exchange_segment={}, transaction_type={}, quantity={}, order_type={}, product_type={}, price={}, trigger_price={}",
                                trade.token, "NSE_FNO", "SELL" ,trade.qty, "STOP_LOSS", trade.prd,
                                trade.slPrice - trade.diff, trade.slPrice
            );
            logger.error(f"error in placing sl order {res['remarks']} ")

        self.tradeManager.updatePartialTrade(trade)
        # logger.info(f"placed sl for a fresh order for {trade.name} with order /number {orderNumber}")


    def cancel_order_and_confirm(self, order_id, max_retries=10, delay=1):
        """
        Cancels the order and polls until it is confirmed canceled.
        Returns True if successfully canceled, False otherwise.
        """
        try:
            logger.info(f"Cancelling stop-loss order: {order_id}")
            res = self.dhan_api.cancel_order(OrderID=order_id)
            logger.info(res)
            # res = 'CANCELLED'
            if res != 'CANCELLED':
                logger.info("Initial cancel request failed:", res)
                return False
            # else:
            #     logger.info("order is cancelled")
            # Now poll until the order is confirmed as canceled
            for attempt in range(max_retries):
                status = self.dhan_api.get_order_status(order_id)
                logger.info(f"Order status: {status}")
                if status == "CANCELLED":
                    logger.info("Order successfully cancelled.")
                    return True
                logger.info(f"Waiting for SL order to cancel... Attempt {attempt+1} with status {status}")
                time.sleep(delay)
            logger.info("Failed to confirm order cancellation after retries.")
            return False
        except Exception as e:
            logger.error("Exception while cancelling order:", e)
            return False



    def manageTrade(self, ltp, trade):
        if not trade.status == 1:
            return

        points = ltp - trade.entryPrice
        targetPoints = trade.targetPoints
        current_time = datetime.now()

        # if targetPoints > 20 and points > 20:
        #     if trade.slPrice < trade.entryPrice +

        # todo: find better logic
        if  targetPoints > 0:
            try:
                if points >= 2.0 / 3 * targetPoints and trade.orderType == "STOP_LOSS":
                    logger.info("modifying sl order from STOP_LOSS to LIMIT")
                    logger.info(f"modifying trade {trade.__str__()}")
                    # ret = self.dhan_api.Dhan.modify_order(order_id=trade.orderNumber, order_type="LIMIT", leg_name="ENTRY_LEG",
                    #                                  quantity=trade.qty, price=trade.targetPrice, trigger_price=0, disclosed_quantity=0, validity='DAY')

                    # res = self.dhan_api.cancel_order(OrderID=trade.orderNumber)
                    # logger.info("order cancelled with response")
                    # logger.info(f"{res}")
                    # time.sleep(1.5)  #to make sure order is cancelled and new order doesnt have margin issues

                    if self.cancel_order_and_confirm( trade.orderNumber):
                        try:
                            res = self.dhan_api.Dhan.place_order(security_id=trade.token, exchange_segment="NSE_FNO", transaction_type="SELL",
                                                            quantity=trade.qty, order_type="LIMIT", product_type=trade.prd,
                                                            price=trade.targetPoints + trade.entryPrice , trigger_price=0)
                            logger.info(res)
                            if res['status'] != 'success':
                                logger.info(f"error in placing new limit order after cancelling sl order  {res['remarks']}")
                            else:
                                logger.info(f"modified placed {trade.name} limit order")
                                logger.info(res)
                                trade.orderNumber = res['data']['orderId']
                                trade.orderType = "LMT"
                                logger.info(
                                    f"{trade.name} sl order modified from STOP_LOSS to LMT with target "
                                    f"{trade.entryPrice + trade.targetPoints}"
                                )
                        except Exception as e:
                            logger.error("failed to place limit convert order {}".format(e))
                    else:
                        logger.error("Could not cancel SL order, aborting limit order placement.")
                        return None
                    # else:
                    #     trade.orderNumber = res['data']['orderId']


                    # trade.orderType = "LMT"
                    # trade.orderNumber = res['data']['orderId']
                    # logger.info(f"{trade.name} sl order modified from STOP_LOSS to LMT with target {trade.entryPrice + trade.targetPoints}")
                if points <= 1.0 / 3 * targetPoints and trade.orderType == "LMT":
                    logger.info("modifying target order from LIMIT to STOP_LOSS")
                    # ret = self.dhan_api.Dhan.modify_order(order_id=trade.orderNumber, order_type="STOP_LOSS", leg_name="ENTRY_LEG",
                    #                                  quantity=trade.qty, price=trade.slPrice, trigger_price=trade.slPrice + trade.diff, disclosed_quantity=0, validity='DAY')

                    # self.dhan_api.cancel_order(OrderID=trade.orderNumber)
                    # logger.info("order cancelled with response")
                    # logger.info(f"{res}")
                    # time.sleep(1.5)

                    if self.cancel_order_and_confirm( trade.orderNumber):
                        try:
                            res = self.dhan_api.Dhan.place_order(security_id=trade.token, exchange_segment="NSE_FNO", transaction_type="SELL",
                                                            quantity=trade.qty, order_type="STOP_LOSS", product_type=trade.prd,
                                                            price=trade.slPrice - trade.diff, trigger_price=trade.slPrice )
                            if res['status'] != 'success':
                                logger.info(f"error in placing new sl order after cancelling limit order {res['remarks']}")
                            else:
                                logger.info(f"modified placed {trade.name} sl order")
                                logger.info(res)
                                trade.orderNumber = res['data']['orderId']
                                trade.orderType = "STOP_LOSS"
                                logger.info(f"{trade.name} limit order modified from "
                                            f"LIMIT to STOP_LOSS with sl {trade.slPrice}")
                        except Exception as e:
                            logger.error("failed to place sl convert order {}".format(e))
                    else:
                        logger.error("Could not cancel LIMIT order, aborting SL order placement.")
                        return None

            except Exception as e:
                logger.error(f"error in modifying order with fix target at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.error(e)

        if trade.targetPoints == 0:
            current_trailing_sl = trade.slPrice
            try:
                ## (A) keeping sl 3 points below latest swing point
                if current_time.second %10 == 0: # TODO: keep calculation at last second only or every 10 sec?
                    logger.info("trail check for new swing point")
                    df = candlestickData.getTokenDf(trade.token)
                    new_sl_time = candlestickData.getMspLow(self.nifty_fut_token, trade)

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
                        logger.info(
                            f"{trade.name} modifying mazor swing point sl from {trade.slPrice} to {new_sl} at candle {new_sl_time}")
                        trade.slPrice = new_sl
            except Exception as e:
                logger.error(f"error in fetching last swing point at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.error(e)

            ## (B) keeping sl 20% below trade peak points
            new_sl = round(ltp * 0.8, 1)
            if new_sl > trade.slPrice + 5:
                logger.info(f"{trade.name} modifying sl from {trade.slPrice} to {new_sl} by  at time {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                trade.slPrice = new_sl


            try:
                if current_time.second %10 ==  0:
                    logger.info(f"trail check for DP cross")
                    df = candlestickData.getTokenDf(trade.token)
                    fut_latest_price = candlestickData.getLatestPrice(self.nifty_fut_token)
                    new_sl_time, dp_price = candlestickData.getCrossedDp(fut_latest_price, self.nifty_fut_token, self.decisionPoints.decisionPoints, trade)
                    if new_sl_time != None and new_sl_time in df['time'].values:
                        # new_sl = df.loc[new_sl_time, 'low'] # low of last candle which crossed dp
                        new_sl = df[df['time'] == new_sl_time]['low'].values[0]
                        # new_sl = round(ltp - abs(dp_price -  fut_latest_price)/2 - 3, 1) -3 # exact dp
                        if new_sl  > trade.slPrice + 5:
                            logger.info(f"{trade.name} modifying sl to below {dp_price} from {trade.slPrice} to {new_sl} with candle {new_sl_time} at time {current_time}")
                            trade.slPrice = new_sl
            except Exception as e:
                logger.error(f"error in getting price below dp at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.error(e)

            #actually modifying sl if its not same as previous sl
            if current_trailing_sl != trade.slPrice:
                logger.info(f"modifying trailing sl from {current_trailing_sl} to {trade.slPrice} at time {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                res=self.dhan_api.Dhan.modify_order(
                    order_id = trade.orderNumber,
                    order_type = "STOP_LOSS",
                    leg_name = "ENTRY_LEG",
                    quantity = trade.qty,
                    price = trade.slPrice,
                    trigger_price = trade.slPrice + 0.5,
                    disclosed_quantity = 0,
                    validity = 'DAY'
                    )
                logger.info(res)

        if ltp < trade.slPrice - 2:
            logger.info("limit sl order crossed by 2 points, exiting all trades with market orders")
            # self.dhan_api.cancel_all_orders()
            self.exit_all_trades(trade)

        self.tradeManager.updatePartialTrade(trade)

    def exit_all_trades(self,trade):
        try:
            if self.cancel_order_and_confirm(trade.orderNumber):
                # self.dhan_api.cancel_order(OrderID=trade.orderNumber)
                logger.info(f"sl crossed, sl order {trade.orderNumber} is cancelled")
                ret = self.dhan_api.Dhan.place_order(
                security_id=trade.token,
                exchange_segment="NSE_FNO",
                transaction_type="SELL",
                quantity=trade.qty,
                order_type="MARKET",
                product_type=trade.prd,
                price=0
                )
                logger.info(ret)
                trade.status = 2
                self.tradeManager.updatePartialTrade(trade)
            # new order placed, how will system know trade is over ?
            # self.dhan_api.cancel_all_orders()
            # tradeManager.removeTrade(trade)
        except Exception as e:
            logger.error(f"error in exiting all trades {e}")



    def manageOptionSl(self, token, ltp):

        if not self.function_lock.acquire(blocking=False):
            logger.info("Another instance is already running, skipping this call.")
            return
        try:
            if not self.tradeManager.isTradeActive(token):
                logger.debug("trade status false or current token is not of current trade")
                return

            trades = self.tradeManager.getTrades(token)
            trade_items = list(trades.items())  # Copy items before submitting

            with ThreadPoolExecutor(max_workers=len(trade_items)) as executor:
                futures = {executor.submit(self.placeSl,  partialTrade): pt for pt, partialTrade in trade_items}
                for future in as_completed(futures):
                    pt = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Error in placing SL for {pt}: {e}")

            trades = self.tradeManager.getTrades(token)
            trade_items = list(trades.items())

            with ThreadPoolExecutor(max_workers=len(trade_items)) as executor:
                futures = {executor.submit(self.manageTrade, ltp, partialTrade): pt for pt, partialTrade in
                           trade_items}
                for future in as_completed(futures):
                    pt = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Error in managing trade for {pt}: {e}")
        finally:
            self.function_lock.release()


    def createTrade(self, token, order_update):
        try:
            #TODO: testing
            # tradeManager.ltps[self.nifty_fut_token] = 22950

            future_ltp = self.tradeManager.ltps[self.nifty_fut_token]

            qty = order_update['quantity']
            entryPrice = order_update['tradedPrice']
            tsym = order_update['displayName']
            product = order_update['product']
            prd = self.dhanHelper.getProductType(product)
            instrument = order_update['instrument']

            slPrice, maxSlPrice, minLotSize, diff, target1, target2 = self.misc.get_sl_and_max_sl_price(instrument, tsym)
            optionType = tsym.split(' ')[-1]

            # slPrice = entryPrice - 10  # TODO: fetch from config
            # maxSlPrice = entryPrice - 12
            # minLotSize = 75

            half = qty // 2
            qty2 = (half // minLotSize) * minLotSize
            qty1 = qty - qty2


            trade1 = PartialTrade(
                name="trade1", status=0, qty=qty1, entryPrice=entryPrice, slPrice=slPrice, maxSlPrice=maxSlPrice,
                targetPoints=target1, orderType="STOP_LOSS", prd=prd, exch="NSE_NFO", tsym=tsym,
                diff=diff, token=token, optionType=optionType
            )
            self.tradeManager.addTrade(token, trade1)
            logger.info(f"trade1 added with qty {qty1}")
            logger.info(f"{trade1}")

            if qty2 > 0:
                trade2 = PartialTrade(
                        name="trade2", status=0, qty=qty2, entryPrice=entryPrice, slPrice=slPrice, maxSlPrice=maxSlPrice,
                        targetPoints=target2, orderType="STOP_LOSS", prd=prd, exch="NSE_NFO", tsym=tsym,
                        diff=diff, token=token, optionType=optionType
                    )

                self.tradeManager.addTrade(token, trade2)
                logger.info(f"trade2 added with qty {qty2}")
                logger.info(f"{trade2}")

            self.shoonya_api.subscribe("NFO|" + str(token))

            # trade = tradeManager.trade
            # trade.targetQtys = [qty1, qty2]
            # trade.targetPrices = self.decisionPoints.getTargetPrices(future_ltp, tradeManager.trade )
            # trade.slPrice = slPrice
            # trade.maxSlPrice = maxSlPrice
            # trade.prd = prd
            # trade.status = 0 # make it elligible for placeSl function
            # logger.info(trade.__str__())
        except Exception as e:
            logger.error(f"Error in creating trade  {e}")

    def handle_buy_order(self, token, order_update):
        try:
            # if tradeManager.isTradeActive(token):
            #   #todo: if trade doesnt exist already
            #     tsym = self.dhan_api.get_trading_symbol(int(token))
            #     optionType = tsym.split(' ')[-1]
            #     trade = PartialTrade(
            #         name="test",  token=token, status=-1, qty=riskManagementobj.qty, entryPrice=order_update['tradedPrice'],
            #         orderType="LIMIT",  exch="NSE_NFO", tsym=tsym, diff=0.2, optionType=optionType, bof=False
            #     )
            #     tradeManager.setTrade(trade)
            #     self.shoonya_api.subscribe("NFO|" + str(token))

            if not self.tradeManager.isTradeActive(token):
                logger.info(f"starting a fresh trade at {datetime.now()} of token {token}");
                self.createTrade(token, order_update)
                self.decisionPoints.updateDecisionPoints(self.tradeManager.ltps[self.nifty_fut_token], order_update['optType'])
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


    def updateSl(self, token, new_sl_price, order_update):
        trades = self.tradeManager.getTrades(token)
        # old_sl_price = trades['trade1'].slPrice
        # trade.slPrice = new_sl_price
        # logger.info(f"old sl price is {old_sl_price} new sl price is {new_sl_price}")

        # return

        old_sl_price = trades["trade1"].slPrice
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
                                    self.dhan_api.Dhan.modify_order,
                                    order_id=partial_trade.orderNumber,
                                    order_type="STOP_LOSS",
                                    leg_name="ENTRY_LEG",
                                    quantity=partial_trade.qty,
                                    price=partial_trade.slPrice - partial_trade.diff,
                                    trigger_price=partial_trade.slPrice ,
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

    def handle_sell_order(self, token, order_update):
        if order_update['txnType'] == 'S' and order_update['status'] == 'Modified' and order_update['orderType'] == 'SL':
            logger.info(f"new manual sl order received for token {token}")
            newSlPrice = order_update['price']
            logger.info(f"new sl price is {newSlPrice}")
            # updateSl(token, newSlPrice, order_update)

        elif order_update['txnType'].upper() == 'S' and order_update['status'].upper() == 'TRADED' and order_update['orderType'].upper() == 'LMT':
            logger.info(f"sell limit order completed")
            logger.info(f"{order_update}")

            try:
                trades = self.tradeManager.getTrades(token)

                for pt, partialTrade in trades.items():
                    if partialTrade.orderNumber == order_update['orderNo']:
                        partialTrade.exitPrice = order_update['tradedPrice']
                        partialTrade.status = 2
                        self.tradeManager.updatePartialTrade(partialTrade)
                        logger.info(f"{pt} completed {partialTrade.__str__()}")

                        if pt == 'trade1':
                            try:# if trade1 is completed, modify trade2 sl to 0
                                if 'trade2' not in trades:
                                    logger.info(f"no trade 2 for this trade")
                                else:
                                    partialTrade2 = trades['trade2']
                                    slPrice = partialTrade2.slPrice
                                    if partialTrade2.slPrice < partialTrade.entryPrice:
                                        partialTrade2.slPrice = partialTrade.entryPrice
                                        self.tradeManager.updatePartialTrade(partialTrade2)
                                        logger.info(f"changed sl of trade2 from {slPrice} to cost at {partialTrade.entryPrice} ")
                            except Exception as e:
                                logger.error(f"trade1 completed, cant modify trade2 {e}")

                flag = True
                for partialTrade in trades.values():
                    if partialTrade.status != 2:
                        flag = False
                        break

                self.riskManagementobj.sanityCheck()

                if flag: # trades are completed
                    logger.info(f"all active trades for token {token} completed")
                    status = self.tradeManager.removeTrade(token)
                    logger.debug(f"token {token} removed from all trades with status {status}")
                    logger.info(f"All trades completed, final Trade is \n {self.tradeManager.trades}")

                    # update last trade time
                    # self.riskManagementobj.sanityCheck()
            except Exception as e:
                logger.error(f"Exception in handling sell order {e}")


    def updateOpenOrders(self):
        orders =  self.dhan_api.Dhan.get_order_list()['data']
        openOrders = []
        for order in orders:
            if order['orderStatus'].upper() == 'PENDING':
                openOrders.append(order)
        update_order_feed(openOrders)


    def handle_order(self, order_update: dict):
        token = order_update['securityId']

        # if order_update['status'] == 'Cancelled' and order_update['txnType'] == 'B':
        #     handle_buy_order(token, order_update)
        #     tradeManager.trade = None

        if order_update['status'] == 'Traded' and order_update['txnType'] == 'B':
            self.handle_buy_order(token, order_update)

        if order_update['txnType']  == 'S':
            self.handle_sell_order(token, order_update)

    # def save_position(self):
    #     try:
    #         position_file = position_folder + datetime.now().strftime('%Y%m%d-%H%M%S') + '.csv'
    #         position_dict = self.dhan_api.Dhan.get_positions()["data"]
    #         positions_df = pd.DataFrame(position_dict)
    #         if positions_df.empty:
    #             return
    #         positions_df.to_csv(position_file, index=False)
    #     except Exception as e:
    #         logger.error(f"error in saving positions {e}")

    def on_order_update(self, order_data: dict):
        """Optional callback function to process order data"""
        print("new order received")
        order_update = order_data.get("Data", {})
        logger.info(order_update)

        # ignore orders other than nifty
        if order_update['displayName'].split(' ')[0] == 'NIFTY':
            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
                executor.submit(self.handle_order, order_update)
                # executor.submit(updateOpenOrders)
                # executor.submit(self.save_position) #TODO: remove it later, only for testing refresh button
                # executor.submit(getOrderBook)
        self.updateOpenOrders()




    def updateTargets(self, targets):
        #TODO: dont allow target modification after 3 minutes  ?

        logger.info("targets are {}, {}".format(targets['t1'], targets['t2']))

        if not self.tradeManager.isTradeActive():
            logger.info("trade is not active")
            send_toast("Targets Update request", "Trade is not active")
            return

        for token in self.tradeManager.trades:
            trades = self.tradeManager.getTrades(token)

            for trade in trades.values():
                if trade.targetModified:
                    send_toast("Not Allowed", "Target already updated once")
                    return

            for trade in trades.values():
                entryPrice = trade.entryPrice
                initialTargetPoints = trade.targetPoints

                # update target based on name
                if trade.name == "trade1":
                    points = targets.get("t1")
                    if points >= 20:
                        trade.targetPoints = points
                        logger.info(f"{trade.name} target changed to {trade.targetPoints}")
                        trade.targetModified = True
                    else:
                        logger.info("not chaging t1 target below 20 points")
                # if trade.name == "trade2":
                #     points = targets.get("t2")
                #     if points >= 20:
                #         trade.targetPoints = targets.get("t2")
                #         logger.info(f"{trade.name} target changed to {trade.targetPoints}")
                #         trade.targetModified = True
                #     else:
                #         logger.info("not chaging t2 target below 20 points")

                # if trade.name == "t3":
                #     trade.set_target_price(targets.get("t3") + entry_price)

                # change limit order price if already in place
                if trade.orderType == "LMT":
                    # ret = self.dhan_api.Dhan.modify_order(order_id=trade.orderNumber, order_type="LIMIT", quantity=trade.qty,
                    #                                  price=trade.targetPoints + trade.entryPrice)
                    ret = self.dhan_api.Dhan.modify_order(
                    order_id = trade.orderNumber,
                    order_type = "LIMIT",
                    leg_name = "ENTRY_LEG",
                    quantity = trade.qty,
                    price = trade.targetPoints + trade.entryPrice,
                    disclosed_quantity = 0,
                    validity = 'DAY')

                    logger.info(
                        "LMT order of trade {} got modified from {} to {}".format(trade.name, entryPrice + initialTargetPoints,
                                                                                  entryPrice + trade.targetPoints))
                    logger.info(ret)
        logger.info("targets modified")
        websocketService.send_toast("Targets Update request", "Targets Updated")
        return 0


    def refreshTrade(self):
        logger.info(f"resetting trades")

        for token in self.tradeManager.trades:
            self.tradeManager.removeTrade(token)

        # cancel all open orders
        data = self.dhan_api.Dhan.get_order_list()["data"]
        if data is None or len(data) == 0:
            pass
        else:
            orders = pd.DataFrame(data)
            if not orders.empty:
                trigger_pending_orders = orders.loc[orders['orderStatus'] == 'PENDING']
                open_orders = orders.loc[orders['orderStatus'] == 'TRANSIT']
                for index, row in trigger_pending_orders.iterrows():
                    response = self.dhan_api.Dhan.cancel_order(row['orderId'])
                for index, row in open_orders.iterrows():
                    response = self.dhan_api.Dhan.cancel_order(row['orderId'])

        position_dict = self.dhan_api.Dhan.get_positions()["data"]
        positions_df = pd.DataFrame(position_dict)
        if positions_df.empty:
            return
        positions_df['netQty'] = positions_df['netQty'].astype(int)
        bought = positions_df.loc[positions_df['netQty'] > 0]


        for index, row in bought.iterrows():
            qty = int(row["netQty"])
            tsym = row["tradingSymbol"]
            token = row["securityId"]
            entryPrice = float(row["costPrice"]) # TODO: is this correct field ?
            prd = "INTRADAY"
            order_update = {'quantity':qty, 'tradedPrice':entryPrice, 'displayName':tsym, 'product':  prd}
            self.createTrade(token, order_update)
            break

