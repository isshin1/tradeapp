# from services import tradeManagement
# from dhanhq import  orderupdate
import asyncio
import concurrent
import os, csv
import logging
from datetime import datetime

import pytz
import requests

from conf.logging_config import logger
import threading
import time
# from dhanhq import DhanContext, MarketFeed, OrderUpdate
from Dependencies.dhanhq import DhanContext, MarketFeed, OrderUpdate
from conf.websocketService import send_price_feed
from models.candlestickData import candlestickData
from conf.config import get_date_folders

''' 
subscribe to dhan order websocketService.py 
'''


class DhanWebsocket:
    def __init__(self, di_container):
        self.di_container = di_container
        self._trade_management = None
        self.config = self.di_container.get('config')
        self.dhan_context = self.di_container.get('dhan_context')
        self.dhan_helper = self.di_container.get('dhan_helper')
        self.checkTokenValidity(self.dhan_context.access_token)
        self.data = None
        self._order_client = None
        self._option_update = None

        self.feed_file = get_date_folders()['feed'] + '/' + str(datetime.now().date()) + ".csv"
        self.tradeManager = self.di_container.get('trade_manager')
        self.dhan_helper = self.di_container.get('dhan_helper')
        self.nifty_fut_token = self.config['nifty_fut_token']
        self.nifty_token = self.config['nifty_token']
        websocket_logger = logging.getLogger("websockets")
        websocket_logger.setLevel(logging.WARNING)
        # self.subscribed_instruments = [
        #     (MarketFeed.NSE_FNO, self.nifty_fut_token, MarketFeed.Ticker),
        #     (MarketFeed.IDX, self.nifty_token, MarketFeed.Ticker),
        # ]
        # self.initialize_feed_file()
        # self.feed_initialized = False
        # self.pending_subscriptions = []
        # self.pending_unsubscriptions = []
        # self.loop = None

    # @property
    # def option_update(self):
    #     """Lazy loading property for option_update_service"""
    #     if self._option_update is None:
    #         self._option_update = self.di_container.get('option_update_service')
    #     return self._option_update
    #
    @property
    def trade_management(self):
        """Lazy loading property for trade_management_service"""
        if self._trade_management is None:
            self._trade_management = self.di_container.get('trade_management_service')
        return self._trade_management

    def run_order_update(self):
        if self._order_client is None:
            self.order_client = OrderUpdate(self.dhan_context)
            self.order_client.on_update = self.trade_management.on_order_update
        while True:
            try:
                self.order_client.connect_to_dhan_websocket_sync()
            except Exception as e:
                logger.error(f"Error connecting to Dhan WebSocket: {e}. Reconnecting in 5 seconds...")
                time.sleep(5)


    # def update_feed(self, token, ltt, ltp):
    #
    #     def get_epoch_from_str(time_str):
    #         kolkata_tz = pytz.timezone('Asia/Kolkata')
    #         today = datetime.now(kolkata_tz).date()
    #         dt = datetime.strptime(f"{today} {time_str}", "%Y-%m-%d %H:%M:%S")
    #         dt_localized = kolkata_tz.localize(dt)
    #         epoch_time = int(dt_localized.timestamp())
    #         return epoch_time
    #
    #     try:
    #         self.tradeManager.ltps[token] = float(ltp)
    #         feed_data = {}
    #
    #         with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    #             futures = []
    #             feed_data['Tsym'] = self.dhan_helper.get_trading_symbol(int(token))
    #             feed_data['tt'] = ltt
    #             feed_data['ltp'] = float(ltp)
    #             feed_data['ft'] = get_epoch_from_str(ltt)
    #             feed_data['token'] = token
    #
    #             futures.append(executor.submit(self.writeFeed, feed_data['tt'], token, feed_data['Tsym'], float(ltp)))
    #             futures.append(executor.submit(self.trade_management.manageOptionSl, token, float(ltp)))
    #             futures.append(executor.submit(send_price_feed, token, ltt, float(ltp)))
    #             futures.append(executor.submit(candlestickData.updateTickData, token, feed_data))
    #             futures.append(executor.submit(self.atm_option_update, token, feed_data))
    #
    #             for future in futures:
    #                 try:
    #                     future.result()
    #                 except Exception as e:
    #                     logger.error(f"Exception occurred while executing a future: {e}")
    #         print(feed_data)
    #     except Exception as err:
    #         logger.error(f"error with feed occured {err}")

    def start_dhan_websocket(self):
        order_thread = threading.Thread(target=self.run_order_update, daemon=True)
        order_thread.start()
        logger.info(f"dhan order websocket started")

    def checkTokenValidity(self, token):
        url = 'https://api.dhan.co/v2/profile'
        headers = {'access-token': token}

        response = requests.get(url, headers=headers)
        res = response.json()
        if 'errorType' in res:
            logger.error("Token is invalid")
        logger.info(response.status_code)