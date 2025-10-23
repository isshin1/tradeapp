# from Dhan_Tradehull import Tradehull
import random
from datetime import datetime, timedelta

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


class DemoAPI:
    """Demo API class that mimics Dhan API behavior for testing purposes"""

    def __init__(self):
        self.demo_orders = {}
        self.demo_positions = {}
        self.order_counter = 1000
        self.demo_balance = 100000

    def _generate_order_id(self):
        self.order_counter += 1
        return str(self.order_counter)

    def _simulate_delay(self):
        time.sleep(random.uniform(0.05, 0.15))

    def place_order(self, security_id, exchange_segment, transaction_type,
                    quantity, order_type, product_type, price=0, trigger_price=0):
        self._simulate_delay()
        order_id = self._generate_order_id()

        # 5% chance of order rejection
        if random.random() < 0.05:
            return {
                'status': 'failure',
                'remarks': 'Demo: Simulated order rejection for testing'
            }

        self.demo_orders[order_id] = {
            'orderId': order_id,
            'securityId': security_id,
            'exchangeSegment': exchange_segment,
            'transactionType': transaction_type,
            'quantity': quantity,
            'orderType': order_type,
            'productType': product_type,
            'price': price,
            'triggerPrice': trigger_price,
            'orderStatus': 'PENDING',
            'tradedPrice': 0,
            'tradedQuantity': 0,
            'timestamp': datetime.now().isoformat()
        }

        logger.info(f"DEMO: Placed {order_type} order {order_id} for {quantity} qty of {security_id}")
        return {'status': 'success', 'data': {'orderId': order_id}}

    def cancel_order(self, OrderID):
        self._simulate_delay()
        if OrderID in self.demo_orders:
            self.demo_orders[OrderID]['orderStatus'] = 'CANCELLED'
            logger.info(f"DEMO: Cancelled order {OrderID}")
            return 'CANCELLED'
        return 'ORDER_NOT_FOUND'

    def modify_order(self, order_id, order_type, leg_name, quantity,
                     price, trigger_price=0, disclosed_quantity=0, validity='DAY'):
        self._simulate_delay()
        if order_id in self.demo_orders:
            order = self.demo_orders[order_id]
            order.update({
                'orderType': order_type,
                'quantity': quantity,
                'price': price,
                'triggerPrice': trigger_price,
                'validity': validity
            })
            logger.info(f"DEMO: Modified order {order_id}")
            return {'status': 'success', 'message': 'Demo order modified'}
        return {'status': 'failure', 'message': 'Demo order not found'}

    def get_order_status(self, order_id):
        return self.demo_orders.get(order_id, {}).get('orderStatus', 'ORDER_NOT_FOUND')

    def get_order_list(self):
        return {'data': list(self.demo_orders.values())}

    def get_positions(self):
        return {'data': list(self.demo_positions.values())}

    def get_trading_symbol(self, token):
        strikes = ['22000', '22500', '23000', '23500', '24000']
        types = ['CE', 'PE']
        return f"NIFTY 01JAN25 {random.choice(strikes)} {random.choice(types)}"



class TradeManagement:
    def __init__(self, di_container):
        self.di_container = di_container
        self.function_lock = threading.Lock()

        self.config = self.di_container.get('config')
        self.nifty_fut_token = self.config['nifty_fut_token']

        self._flattrade_websocket = None
        self._flattrade_api = None
        self._flattrade_helper = None
        self._trade_manager = None
        self._decision_points = None
        self._misc = None
        self._risk_management = None

        self.demo_mode = self.config.get('demo_mode', False)
        if self.demo_mode:
            self.demo_api = DemoAPI()
            logger.info("🎭 DEMO MODE ENABLED - No real trades will be executed")

    @property
    def flattrade_websocket(self):
        if self._flattrade_websocket is None:
            self._flattrade_websocket = self.di_container.get('flattrade_websocket')
        return self._flattrade_websocket

    @property
    def flattrade_api(self):
        if self._flattrade_api is None:
            self._flattrade_api = self.di_container.get('flattrade_api')
        return self._flattrade_api

    @property
    def flattrade_helper(self):
        if self._flattrade_helper is None:
            self._flattrade_helper = self.di_container.get('flattrade_helper')
        return self._flattrade_helper

    @property
    def tradeManager(self):
        if self._trade_manager is None:
            self._trade_manager = self.di_container.get('trade_manager')
        return self._trade_manager

    @property
    def decisionPoints(self):
        if self._decision_points is None:
            self._decision_points = self.di_container.get('decision_points_manager')
        return self._decision_points

    @property
    def misc(self):
        if self._misc is None:
            self._misc = self.di_container.get('misc')
        return self._misc

    @property
    def riskManagementobj(self):
        if self._risk_management is None:
            self._risk_management = self.di_container.get('risk_management_service')
        return self._risk_management

    def _get_api(self):
        """Return demo API if in demo mode, otherwise return real API"""
        if self.demo_mode:
            return self.demo_api
        return self.flattrade_api

    def placeSl(self, trade:PartialTrade):
        if trade.status != 0:
            return
        try:
            api = self._get_api()
            mode_prefix = "DEMO: " if self.demo_mode else ""

            logger.info(f"{mode_prefix}placing sl order for {trade.name} and token {trade.token}")

            res = self.flattrade_helper.place_order(
                 order_type = 'S',
                 product_type = trade.prd,
                 exchange = trade.exch,
                 trading_symbol = trade.tsym,
                 quantity = trade.qty,
                 price_type = 'SL-LMT',
                 price = trade.slPrice - trade.diff,
                 trigger_price = trade.slPrice
            )
            logger.info(res)

            if res['stat'] == "Ok" and 'norenordno' in res :
                orderNumber = res['norenordno']
                trade.orderNumber = orderNumber
                trade.status = 1
                trade.orderType = "SL-LMT"

                logger.info(f"{mode_prefix}{trade.name} placed sl at {trade.slPrice} for a fresh order with order number {orderNumber}")
                logger.info(trade.__str__())

            else:
                logger.error(f"{mode_prefix}{trade.name} error in placing sl order {res['emsg']} ")

            self.tradeManager.updatePartialTrade(trade)
        except Exception as e:
            logger.error(f"{mode_prefix}error in placing sl order {e}")
        # logger.info(f"placed sl for a fresh order for {trade.name} with order /number {orderNumber}")

    def manageTrade(self, ltp, trade, current_time):
        if not trade.status == 1:
            return


        api = self._get_api()
        mode_prefix = "DEMO: " if self.demo_mode else ""
        points = ltp - trade.entryPrice
        targetPoints = trade.targetPoints
        # current_time = datetime.now()


        if current_time.second % 60 == 0:
            pass
        # if targetPoints > 20 and points > 20:
        #     if trade.slPrice < trade.entryPrice +
        if ltp > trade.maxPrice:
            trade.maxPrice = ltp

        # todo: find better logic
        if  targetPoints > 0:
            try:
                if points >= 2.0 / 3 * targetPoints and trade.orderType == "STOP_LOSS":
                    logger.info(f"{mode_prefix}modifying sl order from STOP_LOSS to LIMIT")
                    logger.info(f"{mode_prefix}modifying trade {trade.__str__()}")

                    try:
                        res = self.flattrade_helper.modify_order(
                            exch= trade.exch,
                            tsym = trade.tsym,
                            norenordno = trade.orderNumber,
                            newprice_type = 'LMT',
                            qty = trade.qty,
                            new_price = trade.targetPoints + trade.entryPrice
                        )

                        logger.info(res)
                        if res['stat'] == "Ok" and 'norenordno' in res:
                            logger.info(f"{mode_prefix}modified placed {trade.name} limit order")
                            logger.info(res)
                            trade.orderNumber = res['data']['orderId']
                            trade.orderType = "LMT"
                            logger.info(
                                f"{mode_prefix}{trade.name} sl order modified from STOP_LOSS to LMT with target {trade.entryPrice + trade.targetPoints}")
                        else:
                            logger.info(
                                f"{mode_prefix}error in placing new limit order after cancelling sl order {res['emsg']} ")

                    except Exception as e:
                        logger.error(f"{mode_prefix}failed to place limit convert order {e}")

                if points <= 1.0 / 3 * targetPoints and trade.orderType == "LMT":
                    logger.info(f"{mode_prefix}modifying target order from LIMIT to STOP_LOSS")

                    try:
                        res = self.flattrade_helper.modify_order(
                            exch=trade.exch,
                            tsym=trade.tsym,
                            norenordno=trade.orderNumber,
                            new_price_type='SL-LMT',
                            qty=trade.qty,
                            new_price=trade.slPrice - trade.diff,
                            new_trigger_price = trade.slPrice

                        )
                        if res['stat'] == "Ok" and 'norenordno' in res:
                            logger.info(f"{mode_prefix}modified placed {trade.name} sl order")
                            logger.info(res)
                            trade.orderNumber = res['data']['orderId']
                            trade.orderType = "STOP_LOSS"
                            logger.info(f"{mode_prefix}{trade.name} limit order modified from LIMIT to STOP_LOSS with sl {trade.slPrice}")
                        else:
                            logger.info(
                                f"{mode_prefix}error in placing new limit order after cancelling sl order {res['emsg']} ")
                    except Exception as e:
                        logger.error(f"{mode_prefix}failed to place sl convert order {e}")


                if ltp >= trade.entryPrice +  trade.targetPoints   :
                    logger.info(f"{mode_prefix}{trade.name} entry price {trade.entryPrice} exit price {trade.entryPrice +  trade.targetPoints}")
                    logger.info(f"{mode_prefix}{trade.name} target reached with points {trade.targetPoints} at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    trade.exitPrice = trade.targetPoints
                    trade.status = 2

            except Exception as e:
                logger.error(f"error in modifying order with fix target at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.error(e)

        if trade.targetPoints == 0:
            current_trailing_sl = trade.slPrice
            try:
                ## (A) keeping sl 3 points below latest swing point
                if current_time.second % 10 == 0:
                    # logger.info(f"{mode_prefix}trail check for new swing point")
                    df = candlestickData.getTokenDf(trade.token)
                    new_sl_time = candlestickData.getMspLow(self.nifty_fut_token, trade)

                    if new_sl_time != None and new_sl_time in df['time'].values:
                        new_sl = df[df['time'] == new_sl_time]['low'].values[0]
                    else:
                        new_sl = current_trailing_sl - 3

                    if new_sl > current_trailing_sl + 5:
                        logger.info(f"{mode_prefix}{trade.name} modifying major swing point sl from {current_trailing_sl} to {new_sl} at candle {new_sl_time}")
                        current_trailing_sl = new_sl
            except Exception as e:
                logger.error(f"{mode_prefix}error in fetching last swing point at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.error(e)

            ## (B) keeping sl 20% below trade peak points
            new_sl = round(ltp * 0.8, 1)
            if new_sl > current_trailing_sl + 5:
                logger.info(f"{mode_prefix}{trade.name} modifying sl from {current_trailing_sl} to {new_sl} at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                current_trailing_sl = new_sl

            ## (C) modify sl 3 point below crossed dp

            try:
                if current_time.second % 10 == 0:
                    # logger.info(f"{mode_prefix}trail check for DP cross")
                    df = candlestickData.getTokenDf(trade.token)
                    fut_latest_price = candlestickData.getLatestPrice(self.nifty_fut_token)
                    new_sl_time, dp_price = candlestickData.getCrossedDp(fut_latest_price, self.nifty_fut_token,
                                                                         self.decisionPoints.decisionPoints, trade)
                    if new_sl_time != None and new_sl_time in df['time'].values:
                        new_sl = df[df['time'] == new_sl_time]['low'].values[0]
                        if new_sl > current_trailing_sl + 5:
                            logger.info(
                                f"{mode_prefix}{trade.name} modifying sl to below {dp_price} from {current_trailing_sl} to {new_sl} with candle {new_sl_time} at time {current_time}")
                            current_trailing_sl = new_sl
            except Exception as e:
                logger.error(
                    f"{mode_prefix}error in getting price below dp at time {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                logger.error(e)

            # actually modifying sl if its not same as previous sl
            if current_trailing_sl != trade.slPrice:
                logger.info(
                    f"{mode_prefix}modifying trailing sl from {current_trailing_sl} to {trade.slPrice} at time {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                res = self.flattrade_helper.modify_order(
                    exch=trade.exch,
                    tsym=trade.tsym,
                    norenordno=trade.orderNumber,
                    new_price_type='SL-LMT',
                    qty=trade.qty,
                    new_price=current_trailing_sl ,
                    new_trigger_price=current_trailing_sl + trade.diff

                )
                trade.slPrice = current_trailing_sl
                logger.info(res)

            if ltp < trade.slPrice:
                logger.info(f"{mode_prefix} {trade.name} sl passed, trade exitd with points {round(ltp - trade.entryPrice)}")
                trade.status = 2

            if ltp < trade.maxSlPrice:
                logger.info(f"{mode_prefix}max permitted sl passed, exiting all trades with market orders")
                self.exit_all_trades(trade)

            self.tradeManager.updatePartialTrade(trade)
        self.tradeManager.updatePartialTrade(trade)
        # if trade.status == 2:
        #     logger.info(f"{mode_prefix}trade over")

    def exit_all_trades(self, trade):
        try:
            api = self._get_api()
            mode_prefix = "DEMO: " if self.demo_mode else ""

            res = self.flattrade_helper.modify_order(
                exch=trade.exch,
                tsym=trade.tsym,
                norenordno=trade.orderNumber,
                new_price_type='MKT',
                qty=trade.qty,
                new_price=0.0
            )
            logger.info(res)
            trade.status = 2
            self.tradeManager.updatePartialTrade(trade)
        except Exception as e:
            logger.error(f"{mode_prefix}error in exiting all trades {e}")


    def manageOptionSl(self, token, ltp, current_time=None):
        if current_time is None:
            current_time = datetime.now()

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
                futures = {executor.submit(self.placeSl, partialTrade): pt for pt, partialTrade in trade_items}
                for future in as_completed(futures):
                    pt = futures[future]
                    try:
                        future.result()
                    except Exception as e:
                        logger.error(f"Error in placing SL for {pt}: {e}")

            trades = self.tradeManager.getTrades(token)
            trade_items = list(trades.items())

            with ThreadPoolExecutor(max_workers=len(trade_items)) as executor:
                futures = {executor.submit(self.manageTrade, ltp, partialTrade, current_time): pt for pt, partialTrade in
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

            qty = int(order_update['fillshares'])
            entryPrice = float(order_update['flprc'])
            tsym = order_update['tsym']
            prd = order_update['pcode']
            instrument = None

            slPrice, maxSlPrice, minLotSize, diff, target1, target2 = self.misc.get_sl_and_max_sl_price(instrument, tsym)
            optionType = tsym[-6]

            half = qty // 2
            qty2 = (half // minLotSize) * minLotSize
            qty1 = qty - qty2

            trade1 = PartialTrade(
                name="trade1", status=0, qty=qty1, entryPrice=entryPrice, slPrice=entryPrice-slPrice, maxSlPrice=entryPrice-maxSlPrice,
                targetPoints=target1, orderType="STOP_LOSS", prd=prd, exch="NSE_NFO", tsym=tsym,
                diff=diff, token=token, optionType=optionType
            )
            self.tradeManager.addTrade(token, trade1)
            logger.info(f"trade1 added with qty {qty1}")
            logger.info(f"{trade1}")

            if qty2 > 0:
                trade2 = PartialTrade(
                        name="trade2", status=0, qty=qty2, entryPrice=entryPrice, slPrice=entryPrice-slPrice, maxSlPrice=entryPrice-maxSlPrice,
                        targetPoints=target2, orderType="STOP_LOSS", prd=prd, exch="NSE_NFO", tsym=tsym,
                        diff=diff, token=token, optionType=optionType
                    )

                self.tradeManager.addTrade(token, trade2)
                logger.info(f"trade2 added with qty {qty2}")
                logger.info(f"{trade2}")

            self.flattrade_websocket.subscribe(token)
            websocketService.update_targets(target1, target2)

        except Exception as e:
            logger.error(f"Error in creating trade  {e}")



    def handle_buy_order(self, token, order_update):
        try:
            if not self.tradeManager.isTradeActive(token):
                mode_prefix = "DEMO: " if self.demo_mode else ""
                logger.info(f"{mode_prefix}starting a fresh trade at {datetime.now()} of token {token}")
                self.createTrade(token, order_update)
                # self.decisionPoints.updateDecisionPoints(self.tradeManager.ltps[self.nifty_fut_token], order_update['optType'])
        except Exception as e:
            logger.error(f"Error in handling buy order {e}")

    def updateSl(self, token, new_sl_price, order_update):
        trades = self.tradeManager.getTrades(token)
        old_sl_price = trades["trade1"].slPrice
        executor = None

        if old_sl_price != new_sl_price:
            api = self._get_api()
            mode_prefix = "DEMO: " if self.demo_mode else ""

            logger.info(f"{mode_prefix}modifying all remaining sl from {old_sl_price} to {new_sl_price}")
            try:
                executor = concurrent.futures.ThreadPoolExecutor(max_workers=len(trades))
                futures = []
                for pt, partial_trade in trades.items():
                    partial_trade.slPrice = new_sl_price
                    try:
                        if partial_trade.status == 1:
                            if partial_trade.orderNumber == order_update["orderNo"]:
                                logger.info(f"{mode_prefix}Sl changed manually for trade {partial_trade.name}")
                            else:
                                logger.info(f"{mode_prefix}modifying sl for {partial_trade.name}")
                                future = executor.submit(
                                    self.flattrade_helper.modify_order,
                                    exch=partial_trade.exch,
                                    tsym=partial_trade.tsym,
                                    norenordno=partial_trade.orderNumber,
                                    new_price_type='SL-LMT',
                                    qty=partial_trade.qty,
                                    new_price=partial_trade.slPrice - partial_trade.diff,
                                    new_trigger_price=partial_trade.slPrice
                                )
                                futures.append(future)
                    except Exception as e:
                        logger.error(
                            f"{mode_prefix}Exception occurred during modifying order for trade {partial_trade.name}: {e}")

            finally:
                if executor:
                    executor.shutdown(wait=True)
                    for future in futures:
                        try:
                            future.result()  # Ensure any raised exceptions are caught
                        except Exception as e:
                            logger.error(f"{mode_prefix}Exception occurred during modifying order: {e}")
        else:
            mode_prefix = "DEMO: " if self.demo_mode else ""
            logger.info(f"{mode_prefix}new sl order has same price {old_sl_price}")

    def handle_sell_order(self, token, order_update):
        mode_prefix = "DEMO: " if self.demo_mode else ""

        if order_update['txnType'] == 'S' and order_update['status'] == 'Modified' and order_update[
            'orderType'] == 'SL':
            logger.info(f"{mode_prefix}new manual sl order received for token {token}")
            newSlPrice = order_update['price']
            logger.info(f"{mode_prefix}new sl price is {newSlPrice}")
            # updateSl(token, newSlPrice, order_update)

        elif order_update['txnType'].upper() == 'S' and order_update['status'].upper() == 'TRADED' and order_update[
            'orderType'].upper() == 'LMT':
            logger.info(f"{mode_prefix}sell limit order completed")
            logger.info(f"{order_update}")

            try:
                trades = self.tradeManager.getTrades(token)

                for pt, partialTrade in trades.items():
                    if partialTrade.orderNumber == order_update['orderNo']:
                        partialTrade.exitPrice = order_update['tradedPrice']
                        partialTrade.status = 2
                        self.tradeManager.updatePartialTrade(partialTrade)
                        logger.info(f"{mode_prefix}{pt} completed {partialTrade.__str__()}")

                        if pt == 'trade1':
                            try:  # if trade1 is completed, modify trade2 sl to 0
                                if 'trade2' not in trades:
                                    logger.info(f"{mode_prefix}no trade 2 for this trade")
                                else:
                                    partialTrade2 = trades['trade2']
                                    slPrice = partialTrade2.slPrice
                                    if partialTrade2.slPrice < partialTrade.entryPrice:
                                        partialTrade2.slPrice = partialTrade.entryPrice
                                        self.tradeManager.updatePartialTrade(partialTrade2)
                                        logger.info(
                                            f"{mode_prefix}changed sl of trade2 from {slPrice} to cost at {partialTrade.entryPrice} ")
                            except Exception as e:
                                logger.error(f"{mode_prefix}trade1 completed, cant modify trade2 {e}")

                flag = True
                for partialTrade in trades.values():
                    if partialTrade.status != 2:
                        flag = False
                        break

                if flag:  # trades are completed
                    logger.info(f"{mode_prefix}all active trades for token {token} completed")
                    status = self.tradeManager.removeTrade(token)
                    logger.info(f"{mode_prefix}token {token} removed from all trades with status {status}")
                    logger.info(f"{mode_prefix}All trades completed, final Trade is \n {self.tradeManager.trades}")


            except Exception as e:
                logger.error(f"{mode_prefix}Exception in handling sell order {e}")

            self.riskManagementobj.sanityCheck()

    def updateOpenOrders(self):
        api = self._get_api()
        orders = api.get_order_list()['data']
        openOrders = []
        for order in orders:
            if order.get('orderStatus', '').upper() == 'PENDING':
                openOrders.append(order)
        update_order_feed(openOrders)

    def handle_order(self, order_update: dict):
        token = self.misc.get_token(order_update['tsym'], order_update['exch'])

        if order_update['status'] == 'COMPLETE' and order_update['trantype'] == 'B':
            self.handle_buy_order(token, order_update)

        if order_update['trantype'] == 'S':
            self.handle_sell_order(token, order_update)

    def on_order_update(self, order_data: dict):
        """Optional callback function to process order data"""
        mode_prefix = "DEMO: " if self.demo_mode else ""
        print(f"{mode_prefix}new order received")
        # order_update = order_data.get("Data", {})
        logger.info(order_data)

        # ignore orders other than nifty
        # if order_update['displayName'].split(' ')[0] == 'NIFTY':
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            executor.submit(self.handle_order, order_data)
        # self.updateOpenOrders() TODO: fix orders from flattrade

    def updateTargets(self, targets):
        #TODO: dont allow target modification after 3 minutes  ?
        mode_prefix = "DEMO: " if self.demo_mode else ""
        api = self._get_api()

        t1 , t2 = targets['t1'], targets['t2']
        logger.info(f"{mode_prefix}targets are {t1}, {t2}")

        if not self.tradeManager.isTradeActive():
            logger.info(f"{mode_prefix}trade is not active")
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
                    if t1 > 10:
                        trade.targetPoints = t1
                        logger.info(f"{mode_prefix}{trade.name} target changed to {trade.targetPoints}")
                        trade.targetModified = True
                    else:
                        logger.info(f"{mode_prefix}not chaging t1 target below 20 points")
                        send_toast("Small Target", "Trade Target is smaller than 10")
                        return

                if trade.name == "trade2":
                    if t2 > 10:
                        trade.targetPoints = t2
                        logger.info(f"{trade.name} target changed to {trade.targetPoints}")
                        trade.targetModified = True
                    else:
                        logger.info("not chaging t2 target below 20 points")
                        send_toast("Small Target", "Trade Target is smaller than 10")
                        return
                # if trade.name == "t3":
                #     trade.set_target_price(targets.get("t3") + entry_price)

                # change limit order price if already in place
                if trade.orderType == "LMT":
                    ret = self.flattrade_helper.modify_order(
                        exch=trade.exch,
                        tsym=trade.tsym,
                        norenordno=trade.orderNumber,
                        new_price_type='LIMIT',
                        qty=trade.qty,
                        new_price= trade.targetPoints + trade.entryPrice,
                    )

                    logger.info(
                        "{}, LMT order of trade {} got modified from {} to {}".format(mode_prefix, trade.name, entryPrice + initialTargetPoints,
                                                                                  entryPrice + trade.targetPoints))
                    logger.info(ret)
        logger.info(f"{mode_prefix}targets modified")
        websocketService.send_toast(f"{mode_prefix}Targets Update request", "Targets Updated")
        websocketService.update_targets(t1, t2)
        return 0


    def refreshTrade(self):

        mode_prefix = "DEMO: " if self.demo_mode else ""
        api = self._get_api()
        logger.info(f"{mode_prefix}resetting trades")


        for token in self.tradeManager.trades:
            self.tradeManager.removeTrade(token)



        # self.flattrade_helper.exit_all_market_order()


    def run_feed( self, time, expiry, tsym , dps = [] ):
        try:
            candlestickData.reset()

            month = time.strftime('%m').zfill(2)
            day = time.strftime('%d').zfill(2)
            year = time.strftime('%Y')

            feed_df = pd.read_csv(f'data/feed/{year}/{month}/' + time.strftime('%Y-%m-%d') + '.csv')
            feed_df['time'] = pd.to_datetime(feed_df['time'], format='%Y-%m-%dT%H:%M:%S')
            # token = dhan_api.get_security_id(tsym , "NFO")
            # tsym = "NIFTY 27 MAR 23650 CALL"
            optionType = tsym.split(' ')[-1]

            expiry_day = int(tsym.split(' ')[1])
            expiry_month = int(datetime.strptime(tsym.split(' ')[2].title(), '%b').strftime('%m'))
            expiry = datetime(datetime.now().year, expiry_month, expiry_day)
            # add decision points


            self.decisionPoints.decisionPoints = []
            for dp in dps:
                self.decisionPoints.addDecisionPoint(name=str(dp),price= dp )

            post_entry_df =  feed_df[(feed_df['time'] >= time) & (feed_df['tsym'] == tsym)]
            # post_entry_df_token = feed_df[feed_df['token'] == token]
            post_entry_df_time = feed_df[feed_df['time'] >= time]
            entryPrice = post_entry_df.iloc[0]['price']
            target1, target2 = 25, 0
            token = int(post_entry_df.iloc[0]['token'])
            trade1 = PartialTrade(
                name="trade1", status=0, qty=150, entryPrice=entryPrice, slPrice=entryPrice-10, maxSlPrice=entryPrice-12,
                targetPoints= target1, orderType="STOP_LOSS", prd='INTRADAY', exch="NSE_NFO", tsym=tsym,
                diff=0.2, token=token, optionType=optionType, startTime=time
            )

            trade2 = PartialTrade(
                name='trade2', status=0, qty=75, entryPrice=entryPrice, slPrice=entryPrice-10, maxSlPrice=entryPrice-12,
                targetPoints=target2, orderType="STOP_LOSS", prd='INTRADAY', exch="NSE_NFO", tsym=tsym,
                diff=0.2, token=token, optionType=optionType, startTime=time
            )

            # self.tradeManager.addTrade(token, trade1)
            self.tradeManager.addTrade(token, trade2)


            logger.info(f"starting trade with entry price {entryPrice} at time {time}")
            trade_df = feed_df[feed_df['time'] >= time - timedelta(minutes = 1)]
            trade_df = trade_df[(trade_df['token'] == token) | (trade_df['token'] == int(self.nifty_fut_token))]
            i = 0
            opt_price = 0
            for index, row in trade_df.iterrows():
                tt = row['time']
                token = int(row['token'])
                price = row['price']
                feed_data = {'ltp': price, 'ft': tt.timestamp() }
                candlestickData.updateTickData(token, feed_data)
                if tsym == row['tsym']:
                    opt_price = row['price']
                    if tt is not None:
                        self.tt = tt
                        self.manageOptionSl(token, opt_price, tt)
                        self.tt = None
                    else:
                        pass

                if i%3000 == 0: #
                    pass
                i += 1

                if not self.tradeManager.isTradeActive():
                    break

            if self.tradeManager.isTradeActive():
                trade =  next((trade for trades in [self.tradeManager.getTrades(token) for token in self.tradeManager.trades] for trade in trades.values() if trade.name == "trade2"), None)
                logger.info(f"{trade.name} ended at day close at price {opt_price} with points {round(opt_price - entryPrice)} and max price {trade.maxPrice}")
        except Exception as e:
            logger.error(e)

