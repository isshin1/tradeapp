import os
from datetime import datetime
# from conf.config import   shoonya_api, nifty_fut_token, dhan_api, feed_folder, optionUpdateObj
from conf.logging_config import logger
# from services.tradeManagement import manageOptionSl, setLtps
import threading
# from services.optionUpdate import optionUpdateObj
import time
import concurrent.futures
from conf.websocketService import send_price_feed
from models.candlestickData import candlestickData
import csv
from conf.config import get_date_folders

# from services.charts import chart
# update nifty spot price in consul via feed
class ShoonyaWebsocket:
    def __init__(self, di_container ):
        self.di_container = di_container

        self.config = self.di_container.get('config')
        self.shoonya_api = self.di_container.get('shoonya_api')
        self.dhan_helper = self.di_container.get('dhan_helper')
        self.tradeManager = self.di_container.get('trade_manager')
        self.misc = self.di_container.get('misc')

        self.nifty_fut_token = self.config['nifty_fut_token']
        self.nifty_token = self.config['nifty_token']
        self.feed_file = get_date_folders()['feed'] + '/' + str(datetime.now().date()) + ".csv"

        self._option_update = None
        self._trade_management = None

        self.feed_opened = False
        self.socket_opened = False
        self.feedJson={}
        self.current_chart_token = 0


        self.initialize_feed_file()
        self.current_chart_token = 0
# marketAnalysis.run()



    @property
    def option_update(self):
        """Lazy loading property for option_update_service"""
        if self._option_update is None:
            self._option_update = self.di_container.get('option_update_service')
        return self._option_update

    @property
    def trade_management(self):
        """Lazy loading property for trade_management_service"""
        if self._trade_management is None:
            self._trade_management = self.di_container.get('trade_management_service')
        return self._trade_management


    def initialize_feed_file(self):
        if not os.path.exists(self.feed_file):
            with open(self.feed_file, "w", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["time", "token", "tsym", "price"])  # CSV Headers

    # Function to append data to CSV
    def writeFeed(self, time, token, tsym, price):
        with open(self.feed_file, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([time, token, tsym, price])
        # print(f"Saved: {time}, {token}, {price}")


    # f = open(feed_file, 'a')
    # f.write("time, token, price\n")
    # f.flush()

    # def writeFeed(token, price):
    #     f.write(f"{token}, {price}\n")
    #     f.flush()

    def setChartToken(self, token):
        self.current_chart_token = token


    def atm_option_update(self, token, feed_data):
        try:
            if token != self.nifty_token:
                return

            if self.option_update.init == None:
                self.option_update.getTokens(feed_data['ltp'])
                self.option_update.updateOptions(int(self.tradeManager.ltps[self.nifty_token]))
                self.option_update.init = True
                return

            if feed_data['ft'] % 10 == 0:
                self.option_update.updateOptions(int(self.tradeManager.ltps[self.nifty_token]))
        except Exception as err:
            logger.error(f"error with option update occured {err}")


    def event_handler_feed_update(self, tick_data):
        UPDATE = False
        if 'tk' in tick_data:
            token = tick_data['tk']
            epoch = tick_data.get("ft", int(time.time()))
            timest = datetime.fromtimestamp(epoch).isoformat()
            feed_data = {'tt': timest, 'ft': float(epoch)}

            if 'lp' in tick_data:
                feed_data['ltp'] = float(tick_data['lp'])
            if 'ts' in tick_data:
                feed_data['Tsym'] = str(tick_data['ts'])
            if 'oi' in tick_data:
                feed_data['openi'] = float(tick_data['oi'])
            if 'poi' in tick_data:
                feed_data['pdopeni'] = str(tick_data['poi'])
            if 'v' in tick_data:
                feed_data['Volume'] = str(tick_data['v'])
            if feed_data:
                # print(f"feed data : {feed_data}", flush=True)
                UPDATE = True
                if token not in self.feedJson:
                    self.feedJson[token] = {}
                self.feedJson[token].update(feed_data)
            # logger.info(f"{token} {feed_data}")
            # {'Tsym': 'Nifty 50', 'ltp': 23463.95, 'tt': '2025-03-22T10:35:52', 'ft': 1742621464}
            # {'Tsym': 'NIFTY27MAR25F', 'Volume': '51225', 'ltp': 24100.0, 'openi': 14353050.0, 'pdopeni': '14353050', 'tt': '2025-03-22T10:35:48', 'ft': 1742621464}
            if UPDATE:
                    if 'ltp' in feed_data:
                        try:
                            ltp = float(feed_data['ltp'])
                            self.tradeManager.ltps[token] = ltp
                            # manageOptionSl(token, float(feedJson[token]['ltp']))
                            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                                futures = []
                                if int(token) != 26000:
                                    feed_data['Tsym'] = self.dhan_helper.get_trading_symbol(int(token))
                                else:
                                    feed_data['Tsym'] = "Nifty 50"
                                futures.append(executor.submit(self.writeFeed, feed_data['tt'], token, feed_data['Tsym'],  ltp)) # write feed to a file
                                # futures.append(executor.submit(self.trade_management.manageOptionSl, token, ltp)) # send ltp to trade manager
                                futures.append(executor.submit(send_price_feed, token, epoch, ltp)) # send ltp to frontend
                                # futures.append(executor.submit(self.tradeManagement.setLtps, self.tradeManagement.ltps)) # update ltps globally TODO: fetch from candlestick data instaed ?
                                # futures.append(executor.submit(candlestickData.updateTickData, token, feed_data)) # update candlestick data TODO: update it later on, what does it mean ?
                                futures.append(executor.submit(self.atm_option_update, token, feed_data))
                                for future in futures:
                                    try:
                                        future.result()
                                    except Exception as e:
                                        logger.error(f"Exception occurred while executing a future: {e}")

                        except Exception as err:
                            logger.error(f"error with feed occured {err}")
                        if token == str(self.current_chart_token):
                            tick = {'time': timest, 'price': float(feed_data['ltp']), 'volume': 0}
                            # chart.update_from_tick(pd.Series(tick))
    def update_orders(self, order_update):
        pass
    def event_handler_order_update(self, order_update):
        logger.debug(f"order feed {order_update}")
        try:
            self.update_orders(order_update)
        except Exception as err:
            logger.error(f"update order error occoured {err}")

    def open_callback(self):
        self.feed_opened = True
        print("Shoonya websocketService.py opened")

    def setupWebSocket(self):
        logger.info("waiting for shoonya websocket to open")
        self.shoonya_api.start_websocket(order_update_callback=self.event_handler_order_update,
                             subscribe_callback=self.event_handler_feed_update,
                             socket_open_callback=self.open_callback)
        while(self.feed_opened==False):
            logger.info("waiting for shoonya websocket to open in a loop")
            time.sleep(1)
            pass

    def subscribe(self, token, exchange="NFO"):
        # tsym = self.misc.getSymbol(token)
        tsym = self.dhan_helper.get_trading_symbol(int(token))
        self.shoonya_api.subscribe(exchange + "|" + str(token))
        logger.info(f"subscribed to {tsym} {token}")

    def optionUpdate(self):
        # time.sleep(10)
        while(True):
            if '26000' in self.tradeManager.ltps:
                self.optionUpdateObj.updateOptions(int(self.tradeManager.ltps['26000']))
            time.sleep(60)

    def start_shoonya_websocket(self):
        # Create and start a daemon thread so that it won't block shutdown.
        # thread = threading.Thread(target=setupWebSocket, daemon=True)
        # thread.start()
        self.setupWebSocket()
        logger.info("shoonya websocket started")
        self.shoonya_api.subscribe("NSE|26000")
        self.shoonya_api.subscribe("NFO|"+ str(self.nifty_fut_token))

        logger.info(f"subscribed to NSE|26000 and NFO|{str(self.nifty_fut_token)}")
        #
        # print("starting options update")
        # thread = threading.Thread(target=self.optionUpdate, daemon=True)
        # thread.start()


