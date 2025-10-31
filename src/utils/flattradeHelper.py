
import logging
import json
import yaml
import signal
import os, sys, time
import pyotp
from datetime import date, datetime, timedelta
import pandas as pd
import math
import math
from scipy.stats import norm
from conf.logging_config import logger

from threading import Timer
import pandas as pd
import time
import concurrent.futures
import requests
import hashlib, pyotp

apkversion = "1.0.0"


# # ret = api.login(userid=uid, password=pwd, twoFA=factor2, vendor_code=vc, api_secret=app_key, imei=imei)
# with open('cred.yml') as f:
#     cred = yaml.load(f, Loader=yaml.FullLoader)
#     print(cred)


# totp = pyotp.TOTP(cred['totp_key']).now()
# # print(f'totp is {totp}')
# ret = api.login(userid = cred['user'], password = cred['pwd'], twoFA=totp, vendor_code=cred['vc'], api_secret=cred['api_key'], imei=cred['imei'])
# # ret = api.logout()
# # ret = 'x'


class FlattradeHelper:
    def __init__(self, flattrade_api, cred):
        self.api = flattrade_api
        self.MAX_TRIES = 5
        self.cred = cred


    def killswitch(self):
        logger.info('enabling flattrade killswitch')
        self.exit_all_market_order()
        flattrade_killswitch = FlattradeKillswitch(self.cred)
        flattrade_killswitch.killswitch()

    def check_maxloss(self, pnl):
        print(f'checking max loss with pnl {pnl}')
        try:
            with open('/tmp/maxLoss') as f:
                maxLoss = float(f.readlines()[0].strip('\n'))
                print(f'maxloss is {maxLoss}')
            if pnl == 'NA' or pnl == -1:
                return
            elif pnl < -1 * maxLoss:
                print('max loss crossed')
                ret = self.api.logout()
                exit(0)
        except Exception as e:
            print(f'error is {e}')
    
    
    def get_trade_count(self):
        ret = self.api.get_trade_book()
    
        if ret is None:
            return 0
    
        order_uid = []
        count = 0
        for order in ret:
            order_id = order.get('norenordno')
            if (order_id not in order_uid):
                order_uid.append(order_id)
                if order['trantype'] == "B":
                    count = count + 1
        return count
    
    
    def get_options_brokerage(self, buy_turnover, sell_turnover):
        turnover = buy_turnover + sell_turnover
        stt = round(0.000625 * sell_turnover, 0)
        transct_charges = round(.0005 * turnover, 2)
        sebi = round(.000001 * turnover, 2)
        gst = round(.18 * (transct_charges + sebi), 2)
        stamp_duty = round(.00003 * buy_turnover, 0)
        ipf = round(.000005 * turnover, 2)
        # print(f'stt {stt} trans {transct_charges} gst {gst} sebi {sebi} stamp {stamp_duty} ipf {ipf}')
        # print(f'turnover is {turnover}, sell turnover is {sell_turnover}')
        brokerage = stt + transct_charges + gst + sebi + stamp_duty + ipf
        return brokerage
    
    
    def get_futures_brokerage(self, turnover, sell_turnover):
        brokerage = turnover * 0.0000246 + .0001 * sell_turnover
        return brokerage
    
    
    def get_current_trade_book(self):
        return self.api.get_trade_book()
    
    
    def get_brokerage(self):
        ret = self.api.get_limits()
        brokerage = 0
        if 'brokerage' in ret:
            brokerage = ret['brokerage']
        return float(brokerage)
    
    
    def get_brokerage_old(self):
        ret = self.api.get_trade_book()
        order_uid = []
        sell_turnover, buy_turnover, turnover = 0, 0, 0
    
        # if(ret[0]['trantype'] == 'B'):
        #     return -1
    
        if ret is None:
            return 0
        for order in ret:
            order_id = order.get('norenordno')
            if (order_id not in order_uid):
                order_uid.append(order_id)
                qty = int(order['qty'])
                premium_prc = float(order['avgprc'])
                turnover = turnover + premium_prc * qty
                if order['trantype'] == "S":
                    sell_turnover += premium_prc * qty
                else:
                    buy_turnover += premium_prc * qty
        return self.get_options_brokerage(buy_turnover, sell_turnover)
    
    
    def get_pnl(self):
        ret = self.api.get_positions()
        if ret == None:
            return 0
            # return 1000
        pnl, mtm = 0, 0
        for position in ret:
            pnl += float(position['rpnl'])
            mtm += float(position['urmtom'])
    
        return round(pnl + mtm - self.get_brokerage())


    def get_daily_info(self):
        pnl = self.getPnl()
        brokerage = self.get_brokerage()
        tradebook = self.getTradebook()
        return pnl, tradebook
    
    
    # import random
    def get_ema(self, exchange, token, length):
        # get price info from day start till now
        dayStart = datetime.today().replace(hour=9, minute=15, second=0, microsecond=0)
        endTime = datetime.now()
    
        while True:
            try:
                ret = self.api.get_time_price_series(exchange=exchange, token=token, starttime=dayStart.timestamp(),
                                                endtime=endTime.timestamp(), interval=length)
                break
            except Exception:
                print('Error Fetching information to get ema')
                time.sleep(1)
                continue
    
        if ret == None:
            return
            # return random.randint(1,10)
    
        ret = self.api.get_time_price_series(exchange, token, starttime=dayStart.timestamp(), endtime=endTime.timestamp(),
                                        interval=length)
        df = pd.DataFrame(ret).iloc[::-1]
        df['ema'] = df['intc'].ewm(span=8, adjust=False).mean()
        ema = df['ema'][0]
        return ema    
    

    def modify_order(self, exch, tsym, norenordno, qty, new_price_type, new_price=None, new_trigger_price=None):
        res = {'rejreason': True}
        CURRENT_TRIES = 0
    
        try:
            if new_price_type == 'MKT':
                while res == None or 'rejreason' in res:
                    logger.debug(
                        f"running command api.modify_order(exchange={exch}, trading_symbol={tsym}, orderno={norenordno},\
                        newquantity={qty}, newprice_type='MKT', newprice=0.00)")
                    res = self.api.modify_order(exchange=exch, tradingsymbol=tsym, orderno=norenordno,
                                           newquantity=qty, newprice_type='MKT', newprice=0.00)
                    logger.info(f"res is {res}")
    
                    CURRENT_TRIES += 1
                    time.sleep(0.5)
                    if CURRENT_TRIES >= self.MAX_TRIES:
                        logger.error('Max attempt to modify order failed')
                        break
    
            elif new_price_type == 'SL-LMT':
                while res == None or 'rejreason' in res:
                    logger.debug(
                        f"running command api.modify_order(exchange={exch}, trading_symbol={tsym}, orderno={norenordno}, \
                        newquantity={qty}, newprice_type='SL-LMT', newprice={new_price}, newtrigger_price={new_trigger_price})")
                    res = self.api.modify_order(exchange=exch, tradingsymbol=tsym, orderno=norenordno,
                                           newquantity=qty, newprice_type='SL-LMT', newprice=new_price,
                                           newtrigger_price=new_trigger_price)
                    logger.info(f"res is {res}")
    
                    CURRENT_TRIES += 1
                    time.sleep(0.5)
                    if CURRENT_TRIES >= self.MAX_TRIES:
                        logger.error('Max attempt to modify order failed')
                        break
    
            elif new_price_type == 'LMT':
                while res == None or 'rejreason' in res:
                    logger.debug(
                        f"running command api.modify_order(exchange={exch}, trading_symbol={tsym}, orderno={norenordno}, \
                        newquantity={qty}, newprice_type='LMT', newprice={new_price})")
                    res = self.api.modify_order(exchange=exch, tradingsymbol=tsym, orderno=norenordno,
                                           newquantity=qty, newprice_type='LMT', newprice=new_price)
                    logger.info(f"res is {res}")
    
                    CURRENT_TRIES += 1
                    time.sleep(0.5)
                    if CURRENT_TRIES >= self.MAX_TRIES:
                        logger.error('Max attempt to modify order failed')
                        break
    
    
        except Exception as err:
            print(f'error in modifying order {err}')
            logger.error(f'error in modifying order {err}')
        return res
    
    
    def place_order(self, order_type, product_type, exchange, trading_symbol, quantity, price_type, price,
                   trigger_price=None):
        ''' TODO:
            - fix market and lmt orders
    
        '''
        res = {'rejreason': True}
        CURRENT_TRIES = 0
    
        try:
            if price_type == 'MKT':
                while res == None or 'rejreason' in res:
                    logger.debug(
                        f"running command api.place_order(buy_or_sell={order_type}, product_type={product_type}, exchange={exchange}, \
                         trading_symbol={trading_symbol}, quantity={quantity} , discloseqty=0 ,price_type='LMT', price=0.0, retention='DAY', remarks='market_order') ")
    
                    res = self.api.place_order(buy_or_sell=order_type, product_type=product_type, exchange=exchange,
                                          tradingsymbol=trading_symbol,
                                          quantity=quantity, discloseqty=0, price_type='MKT', price=0, trigger_price=None,
                                          retention='DAY', remarks='market_order')
                    logger.info(f"res is {res}")
    
                    CURRENT_TRIES += 1
                    time.sleep(0.5)
                    if CURRENT_TRIES >= self.MAX_TRIES:
                        logger.error('Max attempt to place order failed')
                        break
    
            elif price_type == 'SL-LMT':
                while res == None or 'rejreason' in res:
                    logger.debug(
                        f"running command api.place_order(buy_or_sell={order_type}, product_type={product_type}, exchange={exchange},\
                         trading_symbol={trading_symbol}, quantity={quantity} , discloseqty=0 ,price_type='SL-LMT', price={price}, trigger_price={trigger_price}, retention='DAY', remarks='stop_loss_order')")
                    res = self.api.place_order(buy_or_sell=order_type, product_type=product_type, exchange=exchange,
                                          tradingsymbol=trading_symbol,
                                          quantity=quantity, discloseqty=0, price_type='SL-LMT', price=price,
                                          trigger_price=trigger_price,
                                          retention='DAY', remarks='stop_loss_order')
                    logger.info(f"res is {res}")
    
                    CURRENT_TRIES += 1
                    time.sleep(0.5)
                    if CURRENT_TRIES >= self.MAX_TRIES:
                        logger.error('Max attempt to place order failed')
                        break
    
            elif price_type == 'LMT':
                while res == None or 'rejreason' in res:
                    logger.debug(
                        f"running command api.place_order(buy_or_sell={order_type}, product_type={product_type}, exchange={exchange},\
                         trading_symbol={trading_symbol},quantity={quantity} , discloseqty=0 ,price_type='LMT', price={price}, retention='DAY', remarks='limit_order')")
                    res = self.api.place_order(buy_or_sell=order_type, product_type=product_type, exchange=exchange,
                                          tradingsymbol=trading_symbol,
                                          quantity=quantity, discloseqty=0, price_type='LMT', price=price, retention='DAY',
                                          remarks='limit_order')
                    logger.info(f"res is {res}")
    
                    CURRENT_TRIES += 1
                    time.sleep(0.5)
                    if CURRENT_TRIES >= self.MAX_TRIES:
                        logger.error('Max attempt to place order failed')
                        break
        except Exception as err:
            print(f'error in placing order {err}')
            logger.error(f'error in placing order {err}')
        return res
    
    
    def cancel_order(self, order):
        res = {'rejreason': True}
        CURRENT_TRIES = 0
    
        try:
            while ('rejreason' in res):
                orderno = order.norenordno  # from place_order return value
                logger.debug(f"cancelling order {order}")
                res = self.api.cancel_order(orderno)
                logger.info(f"res is {res}")
    
                CURRENT_TRIES += 1
                time.sleep(0.5)
                if CURRENT_TRIES >= self.MAX_TRIES:
                    logger.info('Max attempt to cancel order failed')
                    break
        except Exception as err:
            print(f'error in cancelling order {err}')
            logger.error(f'error in cancelling order {err}')
        return res
    

    def get_order_book(self):
        CURRENT_TRIES = 0
    
        try:
            ob = None
            while ob is None:
                ob = self.api.get_order_book()
                CURRENT_TRIES += 1
                time.sleep(0.1)
                if CURRENT_TRIES >= self.MAX_TRIES:
                    logger.info('Max attempts to call orderbook api failed')
                    break
        except Exception as err:
            print(f'error in getting orderbook {err}')
            logger.error(f'error in getting orderbook {err}')
    
        ob = pd.DataFrame(ob)
        return ob
    
    def get_order(self, orderno):
        ob = self.get_order_book(logger)
        for i in ob.itertuples():
            if i.norenordno == orderno:
                return i
        return
    
    
    def get_positions(self):
        CURRENT_TRIES = 0
        try:
            op = None
            while op is None:
                op = self.api.get_positions()
                CURRENT_TRIES += 1
                time.sleep(0.5)
                if CURRENT_TRIES >= self.MAX_TRIES:
                    logger.info('Max attempts to call get_position api failed')
                    break
        except Exception as err:
            # print(f'error in getting positions {err}')
            logger.error(f'error in getting positions {err}')
    
        op = pd.DataFrame(op)
        return op

    def exit_all_market_order(self):

        ob = self.get_order_book()
        logger.debug(f"exiting all positions via market order")

        # cancel/execute all pending orders
        for i in ob.itertuples():
            if i.status == 'TRIGGER_PENDING' or i.status == 'OPEN':  # TODO: check all status of orders/ look into sample code
                if i.trantype == 'S':
                    logger.debug(f"converting all sell orders to market orders")
                    logger.debug(f"running command shoonyaHelper.modifyOrder(api, logger, {i}, \'MKT\')")
                    ret = self.modifyOrder( i, 'MKT')
                    logger.debug(ret)

                if i.trantype == 'B':
                    logger.debug(f"cancelling all buy positions")
                    logger.debug(f"running command shoonyaHelper.modifyOrder(api, logger, {i})")
                    ret = self.cancel_order(i)
                    logger.debug(ret)

        # exit open positions via market orders if any remaining
        op = self.get_positions()
        # close all open positions
        for i in op.itertuples():

            if int(i.netqty) < 0:
                logger.debug(f"closing short position {i} with market order")
                self.place_order('B', i.prd, i.exch, i.tsym, abs(int(i.netqty)), 'MKT', 0)

            if int(i.netqty) > 0:
                logger.debug(f"closing long position {i} with market order")
                self.place_order('S', i.prd, i.exch, i.tsym, int(i.netqty), 'MKT', 0)

    
    def update_ema(self, token, hour, minute):
        exchange = 'NFO'
        multiplier = 0.092
        ema = 0
        # dayStart = datetime.today().replace(hour=9, minute=15, second=0, microsecond=0)
        # endTime = datetime.now()
        dayStart = (datetime.today() - timedelta(days=7)).replace(hour=9, minute=15, second=0, microsecond=0)
        # ret = api.get_time_price_series(exchange=exchange, token=token, starttime=dayStart.timestamp(), interval=1)
    
        endTime = datetime.today().replace(hour=hour, minute=minute, second=0, microsecond=0)
        # print(endTime)
        ret = self.api.get_time_price_series(exchange=exchange, token=token, starttime=dayStart.timestamp(),
                                        endtime=endTime.timestamp(), interval=1)
    
        df = pd.DataFrame(ret)
        df['intc'] = df['intc'].astype(float)
    
        for val in df['intc'][::-1]:
            ema = val * multiplier + ema * (1 - multiplier)
        # print(ema)
        return ema
    

        
def get_sid():
    url = 'https://authapi.flattrade.in/auth/session'

    headers = {
        'Referer': 'https://auth.flattrade.in/',
        'Origin': 'https://auth.flattrade.in'
    }

    response = requests.post(url, headers=headers)
    sid = response.text
    return sid

class FlattradeAuthAutomation:
    def __init__(self, cred):
        self.cred = cred
        self.token_path = "/tmp/flattrade_token.txt"

    def check_session(self, api):
        try:
            pos = api.get_positions()
            return True
        except Exception as e:
            return False

    def get_token(self):
        sid = get_sid()
        headers = {
            'Referer': 'https://auth.flattrade.in/',
            'Origin': 'https://auth.flattrade.in'
        }
        cred = self.cred
        password = cred['pwd']
        api_key = cred['api_key']
        secret_key = cred['secret_key']
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        username = cred['user']

        totp = pyotp.TOTP(cred['totp_key'])
        otp_code = totp.now()

        url = 'https://authapi.flattrade.in/ftauth'
        payload = {
            "UserName": username,
            "Rd": "",
            "Password": password_hash,
            "PAN_DOB": otp_code,
            "App": "",
            "ClientID": "",
            "Key": "",
            "APIKey": api_key,
            "Sid": sid,
            "Override": "",
            "Source": "AUTHPAGE"
        }

        response = requests.post(url, headers=headers, json=payload)

        url = response.json()['RedirectURL']
        code = url.split('code=')[1].split('&')[0]

        sha_str = api_key + code + secret_key
        url = 'https://authapi.flattrade.in/trade/apitoken'
        payload = {
        "api_key": api_key,
        "api_secret": hashlib.sha256(sha_str.encode()).hexdigest(),
        "request_code": code
        }

        response = requests.post(url, headers=headers, json=payload)

        # print(response.text)
        auth_token = response.json().get("token")
        return auth_token

    def login(self, api):
        # api = NorenApiPy()
        cred = self.cred
        username = cred['user']

        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, "r") as f:
                    auth_token = f.read().strip()
                api.set_session(userid= username, password = '', usertoken= auth_token)
            except Exception as e:
                print(f"Failed to read token file: {e}")

        if not self.check_session(api):
        # if True:
            auth_token = self.get_token()
            api.set_session(userid= username, password = '', usertoken= auth_token)
            try:
                with open(self.token_path, "w") as f:
                    f.write(auth_token)
            except Exception as e:
                print(f"Could not save token: {e}")

        return api



class FlattradeKillswitch():
    def __init__(self, cred):
        self.cred = cred
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Origin": "https://auth.flattrade.in",
            "Referer": "https://auth.flattrade.in/",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Python-requests",
        }

    def token_validation(self):
        url = "https://wallapi.flattrade.in/wall/tokenValidation"
        headers = self.headers
        responseA = self.s.get(url, headers=headers)

        headers["TE"] = "trailers"
        responseB = self.s.get(url, headers=headers)
        print(responseA.json(), responseB.json())

    def get_login_token(self):
        url = 'https://authapi.flattrade.in/ftauth'
        password = self.cred['pwd']
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        username = self.cred['user']
        totp = pyotp.TOTP(self.cred['totp_key'])
        otp_code = totp.now()

        payload = {
            "UserName": username,
            "Rd": "",
            "Password": password_hash,
            "PAN_DOB": otp_code,
            "App": "wall",
            "ClientID": "",
            "Key": "",
            "APIKey": "",
            "Sid": self.sid,
            "Override": "",
            "Source": "AUTHPAGE"
        }


        response = self.s.post(url, headers=self.headers, json=payload)
        print(response.text)
        url = response.json()['RedirectURL']
        # print(f"redirect url is {url}")
        token = url.split('token=')[1].split('&')[0]
        login_id = url.split('LoginId=')[1].split('&')[0]
        # print(token, login_id)
        return token, login_id

    def get_session_token(self):
        token, login_id = self.get_login_token()
        url = f'https://wallapi.flattrade.in/wall/token?token={token}&clientId={login_id}'
        response = self.s.get(url, headers=self.headers)
        token = response.json().get("token")
        return token

    def get_killswitch_status(self):
        url2 = 'https://wallapi.flattrade.in/wall/KillSwitch'

        headers = {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Python-requests",
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Origin': 'https://wall.flattrade.in',
            'Sec-GPC': '1',
            'Connection': 'keep-alive',
            'Referer': 'https://wall.flattrade.in/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'DNT': '1',
            'Content-Type': 'application/json'
        }

        response = self.s.get(url2, headers=headers)
        data = response.json()
        # Get all NFO entries
        nfo_segments = [seg for seg in data["segmentDetailsArr"] if seg["segment"] == "BFO"]

        # Get the latest NFO segment (based on disabledDate, if multiple)
        latest_nfo = max(nfo_segments, key=lambda x: x["disabledDate"])

        # Extract the status
        status = latest_nfo["status"]
        print("Latest NFO status:", status)
        if status == 'D':
            return True
        return False

    def killswitch(self):
        self.s = requests.Session()
        self.token_validation()
        self.sid = get_sid()
        token = self.get_session_token()
        self.token_validation()

        killswitch_status = self.get_killswitch_status()
        if killswitch_status:
            logger.info("Kill switch is already active")
            return

        logger.info("enabling killswitch")
        url = 'https://wallapi.flattrade.in/wall/InsertSegmentDetails'

        headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:143.0) Gecko/20100101 Firefox/143.0',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Origin': 'https://wall.flattrade.in',
            'Sec-GPC': '1',
            'Connection': 'keep-alive',
            'Referer': 'https://wall.flattrade.in/',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-site',
            'DNT': '1',
            'Content-Type': 'application/json'
        }
        payload =[
            {"segment":"BFO","segmentDisplay":"BSE - Future & Option","status":"N","disabledDate":""},
            {"segment":"NFO","segmentDisplay":"NSE - Future & Option","status":"N","disabledDate":""},
        ]
        response = self.s.post(url, json=payload, headers=headers)
        print(f"Response: {response.text}")

        self.get_killswitch_status()