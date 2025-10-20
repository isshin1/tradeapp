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
        auth_token = self.get_token()
        return api.set_session(userid= username, password = '', usertoken= auth_token)

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

    def killswitch(self):
        self.s = requests.Session()
        self.sid = get_sid()
        token = self.get_session_token()

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
            # {"segment": "BSE", "segmentDisplay": "BSE - Equity", "status": "N", "disabledDate": ""}
        ]
        response = self.s.post(url, json=payload, headers=headers)
        print(f"Response: {response.text}")

        url2 = 'https://wallapi.flattrade.in/wall/KillSwitch'

        response = self.s.get(url2, headers=headers)
        print("KillSwitch Response:")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")



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