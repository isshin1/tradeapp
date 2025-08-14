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

# from services.charts import chart
# update nifty spot price in consul via feed
class ShoonyaWebsocket:
    def __init__(self, config, tradeManagement, tradeManager, shoonya_api, nifty_fut_token, dhan_api, feed_folder, optionUpdateObj ):
        self.config = config
        self.feed_opened = False
        self.socket_opened = False
        self.feedJson={}
        self.current_chart_token = 0
        self.tradeManagement = tradeManagement
        self.tradeManager = tradeManager
        self.shoonya_api = shoonya_api
        self.nifty_fut_token = nifty_fut_token
        self.dhan_api = dhan_api
        self.optionUpdateObj = optionUpdateObj
        self.feed_file = feed_folder + str(datetime.now().date()) + ".csv"
        self.initialize_feed_file()
        self.current_chart_token = 0
# marketAnalysis.run()

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

    def event_handler_feed_update(self, tick_data):
        UPDATE = False
        if 'tk' in tick_data:
            token = tick_data['tk']
            timest = datetime.fromtimestamp(int(tick_data['ft'])).isoformat()
            epoch = tick_data.get("ft")
            feed_data = {'tt': timest, 'ft': epoch}

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
                            self.tradeManager.ltps[token] = float(feed_data['ltp'])
                            # manageOptionSl(token, float(feedJson[token]['ltp']))
                            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                                futures = []
                                if 'Tsym' not in feed_data and int(token) != 26000:
                                    feed_data['Tsym'] = self.dhan_api.get_trading_symbol(int(token))
                                    futures.append(executor.submit(self.writeFeed, feed_data['tt'], token, feed_data['Tsym'],  float(self.feedJson[token]['ltp']))) # write feed to a file
                                futures.append(executor.submit(self.tradeManagement.manageOptionSl, token, float(self.feedJson[token]['ltp']))) # send ltp to trade manager
                                futures.append(executor.submit(send_price_feed, token, epoch, float(self.feedJson[token]['ltp']))) # send ltp to frontend
                                # futures.append(executor.submit(self.tradeManagement.setLtps, self.tradeManagement.ltps)) # update ltps globally TODO: fetch from candlestick data instaed ?
                                futures.append(executor.submit(candlestickData.updateTickData, token, feed_data)) # update candlestick data TODO: update it later on, what does it mean ?
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


    def optionUpdate(self):
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
        self.shoonya_api.subscribe("NFO|"+self.nifty_fut_token)

        logger.info(f"subscribed to NSE|26000 and NFO|{self.nifty_fut_token}")

        print("starting options update")
        thread = threading.Thread(target=self.optionUpdate, daemon=True)
        thread.start()


