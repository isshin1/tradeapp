import os
from datetime import datetime
from conf.config import logger,  shoonya_api, nifty_fut_token, dhan_api
from services.tradeManagement import manageOptionSl, setLtps
import threading
from services.optionUpdate import optionUpdateObj
import time
import concurrent.futures
from conf.websocketService import send_price_feed
import csv

# from services.charts import chart
# update nifty spot price in consul via feed
feed_opened = False
socket_opened = False
feedJson={}
ltps=dict()
current_chart_token = 0

feed_file = "data/feed/" + str(datetime.now().date()) + ".csv"

# marketAnalysis.run()

def initialize_feed_file():
    if not os.path.exists(feed_file):
        with open(feed_file, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["time", "token", "tsym", "price"])  # CSV Headers

initialize_feed_file()
# Function to append data to CSV
def writeFeed(time, token, tsym, price):
    with open(feed_file, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([time, token, tsym, price])
    # print(f"Saved: {time}, {token}, {price}")


# f = open(feed_file, 'a')
# f.write("time, token, price\n")
# f.flush()

# def writeFeed(token, price):
#     f.write(f"{token}, {price}\n")
#     f.flush()

def setChartToken(token):
    global current_chart_token
    current_chart_token = token

def event_handler_feed_update(tick_data):
    global current_chart_token
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
            if token not in feedJson:
                feedJson[token] = {}
            feedJson[token].update(feed_data)
        # logger.info(f"{token} {feed_data}")
        ## TODO: paste a sample feedjson here
        # {'Tsym': 'Nifty 50', 'ltp': 23463.95, 'tt': '2025-03-22T10:35:52', 'ft': 1742621464}
        # {'Tsym': 'NIFTY27MAR25F', 'Volume': '51225', 'ltp': 24100.0, 'openi': 14353050.0, 'pdopeni': '14353050', 'tt': '2025-03-22T10:35:48', 'ft': 1742621464}
        if UPDATE:
                if 'ltp' in feed_data:
                    try:
                        ltps[token] = float(feed_data['ltp'])
                        # manageOptionSl(token, float(feedJson[token]['ltp']))
                        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                            futures = []
                            if 'Tsym' not in feed_data and int(token) != 26000:
                                feed_data['Tsym'] = dhan_api.get_trading_symbol(int(token))
                                futures.append(executor.submit(writeFeed, feed_data['tt'], token, feed_data['Tsym'],  float(feedJson[token]['ltp']))) # write feed to a file
                            futures.append(executor.submit(manageOptionSl, token, float(feedJson[token]['ltp']))) # send ltp to trade manager
                            futures.append(executor.submit(send_price_feed, token, epoch, float(feedJson[token]['ltp']))) # send ltp to frontend
                            futures.append(executor.submit(setLtps, ltps)) # update ltps globally TODO: fetch from candlestick data instaed ?
                            # futures.append(executor.submit(candlestickData.updateTickData, token, feed_data)) # update candlestick data TODO: update it later on
                            for future in futures:
                                try:
                                    future.result()
                                except Exception as e:
                                    logger.error(f"Exception occurred while executing a future: {e}")

                    except Exception as err:
                        logger.error(f"error with feed occured {err}")
                    if token == str(current_chart_token):
                        tick = {'time': timest, 'price': float(feed_data['ltp']), 'volume': 0}
                        # chart.update_from_tick(pd.Series(tick))
def update_orders(order_update):
    pass
def event_handler_order_update(order_update):
    logger.debug(f"order feed {order_update}")
    try:
        update_orders(order_update)
    except Exception as err:
        logger.error(f"update order error occoured {err}")

def open_callback():
    global feed_opened
    feed_opened = True
    print("Shoonya websocketService.py opened")

def setupWebSocket():
    global feed_opened
    logger.info("waiting for shoonya websocket to open")
    shoonya_api.start_websocket(order_update_callback=event_handler_order_update,
                         subscribe_callback=event_handler_feed_update,
                         socket_open_callback=open_callback)
    while(feed_opened==False):
        logger.info("waiting for shoonya websocket to open in a loop")
        time.sleep(1)
        pass


def optionUpdate():
    while(True):
        if '26000' in ltps:
            optionUpdateObj.updateOptions(int(ltps['26000']))
        time.sleep(60)

def start_shoonya_websocket():
    # Create and start a daemon thread so that it won't block shutdown.
    # thread = threading.Thread(target=setupWebSocket, daemon=True)
    # thread.start()
    setupWebSocket()
    logger.info("shoonya websocket started")
    shoonya_api.subscribe("NSE|26000")
    shoonya_api.subscribe("NFO|"+nifty_fut_token)

    logger.info(f"subscribed to NSE|26000 and NFO|{nifty_fut_token}")

    print("starting options update")
    thread = threading.Thread(target=optionUpdate, daemon=True)
    thread.start()


