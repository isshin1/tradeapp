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

    @property
    def riskManagementobj(self):
        if self._risk_management is None:
            self._risk_management = self.di_container.get('risk_management_service')
        return self._risk_management

    def run_order_update(self):
        if self._order_client is None:
            self.order_client = OrderUpdate(self.dhan_context)
            self.order_client.on_update = self.riskManagementobj.sanityCheck
        while True:
            try:
                self.order_client.connect_to_dhan_websocket_sync()
            except Exception as e:
                logger.error(f"Error connecting to Dhan WebSocket: {e}. Reconnecting in 5 seconds...")
                time.sleep(5)

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