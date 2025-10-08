from NorenRestApiPy.NorenApi import NorenApi
from threading import Timer
import pandas as pd
import time
import concurrent.futures
import requests
import hashlib, pyotp

api = None


class Order:
    def __init__(self, buy_or_sell: str = None, product_type: str = None,
                 exchange: str = None, tradingsymbol: str = None,
                 price_type: str = None, quantity: int = None,
                 price: float = None, trigger_price: float = None, discloseqty: int = 0,
                 retention: str = 'DAY', remarks: str = "tag",
                 order_id: str = None):
        self.buy_or_sell = buy_or_sell
        self.product_type = product_type
        self.exchange = exchange
        self.tradingsymbol = tradingsymbol
        self.quantity = quantity
        self.discloseqty = discloseqty
        self.price_type = price_type
        self.price = price
        self.trigger_price = trigger_price
        self.retention = retention
        self.remarks = remarks
        self.order_id = None


# print(ret)


def get_time(time_string):
    data = time.strptime(time_string, '%d-%m-%Y %H:%M:%S')

    return time.mktime(data)

class FlattradeAuthAutomation:
    def __init__(self, cred):
        self.cred = cred

    def get_sid(self):
        url = 'https://authapi.flattrade.in/auth/session'

        headers = {
            'Referer': 'https://auth.flattrade.in/',
            'Origin': 'https://auth.flattrade.in'
        }

        response = requests.post(url, headers=headers)
        sid = response.text
        return sid

    def get_token(self):
        sid = self.get_sid()
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
        auth_token = self.get_token()
        return api.set_session(userid= username, password = '', usertoken= auth_token)

class NorenApiPy(NorenApi):
    def __init__(self):
        # NorenApi.__init__(self, host='https://piconnect.flattrade.in/PiConnectTP/', websocket='wss://piconnect.flattrade.in/PiConnectWSTp/', eodhost='https://web.flattrade.in/chartApi/getdata/')
        NorenApi.__init__(self, host='https://piconnect.flattrade.in/PiConnectTP/',
                          websocket='wss://piconnect.flattrade.in/PiConnectWSTp/')

        global api
        api = self

    def place_basket(self, orders):

        resp_err = 0
        resp_ok = 0
        result = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:

            future_to_url = {executor.submit(self.place_order, order): order for order in orders}
            for future in concurrent.futures.as_completed(future_to_url):
                url = future_to_url[future]
            try:
                result.append(future.result())
            except Exception as exc:
                print(exc)
                resp_err = resp_err + 1
            else:
                resp_ok = resp_ok + 1

        return result

    def placeOrder(self, order: Order):
        ret = NorenApi.place_order(self, buy_or_sell=order.buy_or_sell, product_type=order.product_type,
                                   exchange=order.exchange, tradingsymbol=order.tradingsymbol,
                                   quantity=order.quantity, discloseqty=order.discloseqty, price_type=order.price_type,
                                   price=order.price, trigger_price=order.trigger_price,
                                   retention=order.retention, remarks=order.remarks)
        # print(ret)

        return ret