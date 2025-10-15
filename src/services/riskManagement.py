from math import ceil

from conf.logging_config import logger

import os, subprocess
from datetime import datetime, time
import threading
from conf.websocketService import update_timer

# from services.pihole import pihole
class RiskManagement:
    # def __init__(self, config, dhan_api, dhan_helper ):
    def __init__(self, di_container):
        self.di_container = di_container

        # Get only the essential dependencies immediately
        self.config = self.di_container.get('config')
        self.dhan_api = self.di_container.get('dhan_api')
        self.dhan_helper = self.di_container.get('dhan_helper')

        self.pnl = 0
        self.peakPnl = 0
        self.tradeCount = 0
        self.maxTradeCount = self.config['intraday']['maxTradeCount']
        # self.qty = self.get_buy_qty('NIFTY')
        self.maxLoss = self.config['intraday']['maxLoss']
        self.lastTradeTime = datetime.today().replace(hour=0, minute=0)
        self.margin = self.dhan_helper.get_balance()

        # self.scheduler2 = threading.Timer(1, self.wait_timer)
        # self.scheduler2.start()
        logger.info(f"max loss is {self.maxLoss}")

    def getQty(self, price):
        qty = self.qty
        # reduce quantity if margin is insufficient
        while self.margin < price * qty and qty > 75:
            qty -= 75

        # if loss is already more than 10 points, reduce qty to half
        if self.pnl  < -1 * self.qty * 10:
            qty  =  qty /2 if qty %2 == 0 else (qty - 75) / 2

        if qty < 75:
            qty = 75

        return qty

    def update(self):
        self.tradeCount = self.dhan_helper.getTradeCount()
        # self.pnl = self.dhan_helper.getPnl() - (40 + self.qty * 25 / 75) * self.tradeCount # TODO: change the brokerage function, appromixated currently
        self.pnl = self.dhan_helper.getPnl()

        if(self.pnl > self.peakPnl):
            self.peakPnl = self.pnl
        self.margin = self.dhan_helper.get_balance()

    def maxLossCrossed(self):
        self.update()
        if self.pnl - self.peakPnl <= -1 * self.maxLoss:
            logger.info("cumulative max loss crossed")
            return True
        if self.tradeCount >= self.maxTradeCount:
            logger.info("max trades crossed")
            return True
        if self.pnl  <= -1 * self.maxLoss :
            logger.info("next trade will cross maxloss, auto exiting ")
            return True
        return False

    def get_buy_qty(self, index_name):
        indexes = self.config.get('intraday', {}).get('indexes', [])
        for index in indexes:
            if index.get('name') == index_name:
                qty = index.get('buyQty')
                logger.info(f"buy quantity is {qty}")
                return qty
        return 0

    def is_trading_session(self):
        start_time = time(9, 0)
        end_time = time(15, 30)
        return datetime.now().time() > start_time and datetime.now().time() < end_time

    def endSession(self, force=True):

        if not self.is_trading_session():
            logger.info("not trading session, skipping killswitch")
            return

        self.update()
        logger.info(f"turning killswitch on with trades {self.tradeCount} and pnl {self.pnl}")
        self.dhan_helper.cancel_all_orders()
        self.dhan_helper.kill_switch('ON')
        if force:
            self.dhan_helper.kill_switch('OFF')
            return self.dhan_helper.kill_switch('ON')

    def killswitch(self):
        if self.maxLossCrossed():
            return self.endSession()
        return None


    def lockScreen(self):
        cmd_lock = ["hyprlock", "-c", "/home/kushy/.config/hypr/hyprlock-trade.conf"]
        cmd_suspend = ["systemctl", "suspend"]

        if os.path.exists('/.dockerenv'):
            result = subprocess.run(["docker", "run", "--rm", "alpine", "sh", "-c", cmd_lock], capture_output=True, text=True)
        else:
            subprocess.run(cmd_lock, capture_output=True, text=True)
            # subprocess.run(cmd_suspend, capture_output=True, text=True)


    def overTrading(self):
        diff = (datetime.now() - self.lastTradeTime).total_seconds() / 60
        diff = ceil(diff)
        if diff < 3:
            return 3 - diff
        return 0

    def sanityCheck(self, *args, **kwargs):
        print(args)
        print(kwargs)

        self.lastTradeTime = datetime.now()
        logger.info("running sanity check")
        thread1 = threading.Thread(target=self.killswitch)
        # thread2 = threading.Thread(target=self.lockScreen)

        # Start both threads
        thread1.start()
        # thread2.start()

        # Wait for both threads to complete
        thread1.join()
        # thread2.join()

        # pihole.enablePihole()

    def periodic_check(self):
        self.killswitch()
        self.scheduler = threading.Timer(60, self.periodic_check)
        self.scheduler.start()

    def wait_timer(self):
        diff = (datetime.now() - self.lastTradeTime).total_seconds()
        if diff < 15* 60:
            seconds_left = int(15*60 - diff)
            minutes_left = str(int(seconds_left / 60)).zfill(2)
            seconds_left = str(seconds_left % 60).zfill(2)
            time_left = f"{minutes_left}:{seconds_left}"
            update_timer(time_left)
            self.scheduler2 = threading.Timer(1, self.wait_timer)
            self.scheduler2.start()




