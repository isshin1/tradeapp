# from models.TradeManager import tradeManager
import math, mibian
import time
from datetime import datetime
from conf import websocketService
# from services.tradeManagement import updateOpenOrders
from conf.logging_config import logger
from conf.websocketService import update_fut

# r = redis.Redis(host='localhost', port=6379, db=0)

# from conf.shoonyaWebsocket import setChartToken
class OptionUpdate:
    # def __init__(self, config, dhan_api, shoonya_api,  misc, tradeManagement, tradeManager, nifty_fut_token, nifty_fut_symbol):
    def __init__(self, di_container):
        self.di_container = di_container
        self.dhan_websocket = self.di_container.get('dhan_websocket')
        self.shoonya_websocket = self.di_container.get('shoonya_websocket')

        self.config = self.di_container.get('config')
        self.dhan_api = self.di_container.get('dhan_api')
        self.shoonya_api = self.di_container.get('shoonya_api')
        self.dhan_helper = self.di_container.get('dhan_helper')
        self.trade_manager = self.di_container.get('trade_manager')
        self.decision_points = self.di_container.get('decision_points_manager')
        misc = self.di_container.get('misc')
        # risk_management = self.di_container.get('risk_management_service')
        trade_management = self.di_container.get('trade_management_service')
        self.delta = self.config['intraday']['delta']
        self.callPrice = None
        self.putPrice = None
        self.expiry_date = self.config['nifty_weekly_expiry']

        self.subscribedTokens = ['26000']
        # self.ltp = self.getLtp()
        # self.getTokens(self.ltp)
        self.init = None
        self.misc = misc
        self.tradeManagement = trade_management
        # self.tradeManager = trade_manager
        self.fut_token = self.config['nifty_fut_token']
        self.fut_symbol = self.config['nifty_fut_symbol']
        logger.info(f"using expiry {self.expiry_date}")

    def getLtp(self):
        res = self.shoonya_api.get_quotes(exchange="NSE", token='26000')
        ltp =  int(float(res['lp']))
        return round(ltp / 50) * 50

    def getTokens(self, ltp):
        spot_price = round(ltp / 50) * 50
        self.callSymbol = "NIFTY " + self.expiry_date.strftime("%d %b ").upper() + str(spot_price) + " CALL"
        self.putSymbol = "NIFTY " +  self.expiry_date.strftime("%d %b ").upper() + str(spot_price) + " PUT"
        self.callToken = self.dhan_helper.get_security_id(self.callSymbol, "NFO")
        self.putToken = self.dhan_helper.get_security_id(self.putSymbol, "NFO")

    def  getCallDelta(self, strike_price, spot_price):
        current_date = datetime.now().strftime('%d-%m-%y')
        # expiry_date = misc.get_nse_weekly_expiry('NIFTY', 0)

        # expiry = datetime.strptime(expiry_date, '%d-%m-%y').replace(hour=15, minute=30, second=0, microsecond=0)
        expiry = self.expiry_date.replace(hour=15, minute=30, second=0, microsecond=0)
        now = datetime.strptime(current_date, '%d-%m-%y')

        seconds = math.floor((expiry-now).total_seconds())
        minutes = math.floor(seconds/60)
        hours = math.floor(minutes/60)
        days = seconds/86400

        c = mibian.BS([spot_price, strike_price, 7, days], volatility=18)
        return c.callDelta

    def find_index_descending(self, lst):
        for index in range(len(lst) - 1, -1, -1):
            if lst[index] > self.delta:
                return index
        return -1

    def find_index_ascending(self, lst):
        for index, value in enumerate(lst):
            if value > self.delta:
                return index
        return -1

    def updateOptions(self, spot_price:int = 0, firstFetch=False ):

        # do not update options if trade is active
        if self.trade_manager.isTradeActive():
            return

        if spot_price == 0:
            spot_price = self.trade_manager.ltps[self.config['nifty_token']]
        # else:
        # spot_price = round(spot_price / 50) * 50

        spot_price = round(spot_price / 50) * 50

        strike_list = list(range(spot_price - 5*50, spot_price + 5*50 + 1, 50))
        call_delta_list = list(map(lambda x: self.getCallDelta(x, spot_price), strike_list))
        put_delta_list = list(map(lambda x: 1 - x, call_delta_list))

        callPrice = strike_list[self.find_index_descending(call_delta_list)]
        putPrice = strike_list[self.find_index_ascending(put_delta_list)]
        #
        # if firstFetch:
        #     self.callPrice = 0
        #     self.putPrice = 0
        #     self.subscribedTokens = ['26000']

        flag = 0
        if callPrice != self.callPrice:
            self.callPrice = callPrice
            self.callSymbol = "NIFTY " +  self.expiry_date.strftime("%d %b ").upper() + str(callPrice) + " CALL"
            # self.shoonya_api.unsubscribe("NFO|"+ str(self.callToken))
            self.callToken = self.dhan_helper.get_security_id(self.callSymbol, "NFO")
            if self.callToken not in self.subscribedTokens:
                self.shoonya_websocket.subscribe(str(self.callToken))
                # self.dhan_websocket.subscribe(self.callToken)
                self.subscribedTokens.append(self.callToken)

            flag = 1

        if putPrice != self.putPrice:
            self.putPrice = putPrice
            self.putSymbol = "NIFTY " +  self.expiry_date.strftime("%d %b ").upper() + str(putPrice) + " PUT"
            # self.shoonya_api.unsubscribe("NFO|"+ str(self.putToken))
            self.putToken = self.dhan_helper.get_security_id(self.putSymbol, "NFO")
            if self.putToken not in self.subscribedTokens:
                self.shoonya_websocket.subscribe(str(self.putToken))
                # self.dhan_websocket.subscribe(self.putToken)
                self.subscribedTokens.append(self.putToken)
            flag = 1

        if flag == 1 or firstFetch:
            websocketService.update_atm_options(self.callToken, self.callSymbol, self.putToken, self.putSymbol)
            websocketService.update_fut(self.fut_token, self.fut_symbol)
            self.tradeManagement.updateOpenOrders()
            # r.publish('channel1', f"{self.callToken} {self.callSymbol} {self.putToken} {self.putSymbol}")
            # changeChart(self.callToken)

