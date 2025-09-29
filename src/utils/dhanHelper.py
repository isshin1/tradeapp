# from conf.config import dhan_api
from conf.logging_config import logger
import requests
import os, sys, time
from conf.config import BASE_DIR
import pandas as pd
from datetime import datetime

class DhanHelper:
    def __init__(self, dhan_api):
        self.dhan_api = dhan_api
        self.instrument_df = self.get_instrument_file()

    def get_instrument_file(self):
        global instrument_df
        base_folder = BASE_DIR + "/Dependencies/"
        current_date = time.strftime("%Y-%m-%d")
        expected_file = 'all_instrument ' + str(current_date) + '.csv'
        for item in os.listdir(base_folder):
            path = os.path.join(item)

            if (item.startswith('all_instrument')) and (current_date not in item.split(" ")[1]):
                if os.path.isfile(base_folder + path):
                    os.remove(base_folder + path)
        if expected_file in os.listdir(base_folder):
            try:
                print(f"reading existing file {expected_file}")
                instrument_df = pd.read_csv(base_folder + expected_file, low_memory=False)
            except Exception as e:
                print(
                    "This BOT Is Instrument file is not generated completely, Picking New File from Dhan Again")
                instrument_df = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master.csv", low_memory=False)
                instrument_df['SEM_CUSTOM_SYMBOL'] = instrument_df['SEM_CUSTOM_SYMBOL'].str.strip().str.replace(r'\s+',
                                                                                                                ' ',
                                                                                                                regex=True)
                instrument_df.to_csv(base_folder + expected_file)
        else:
            # this will fetch instrument_df file from Dhan
            print("This BOT Is Picking New File From Dhan")
            instrument_df = pd.read_csv("https://images.dhan.co/api-data/api-scrip-master.csv", low_memory=False)
            instrument_df['SEM_CUSTOM_SYMBOL'] = instrument_df['SEM_CUSTOM_SYMBOL'].str.strip().str.replace(r'\s+', ' ',
                                                                                                            regex=True)
            instrument_df.to_csv(base_folder + expected_file)
        return instrument_df


    def get_security_id(self, tradingsymbol: str, exchange: str):
        tradingsymbol = tradingsymbol.upper()
        instrument_df = self.instrument_df.copy()

        instrument_exchange = {'NSE': "NSE", 'BSE': "BSE", 'NFO': 'NSE', 'BFO': 'BSE', 'MCX': 'MCX', 'CUR': 'NSE'}

        security_check = instrument_df[((instrument_df['SEM_TRADING_SYMBOL'] == tradingsymbol) | (
                instrument_df['SEM_CUSTOM_SYMBOL'] == tradingsymbol)) & (
                                               instrument_df['SEM_EXM_EXCH_ID'] == instrument_exchange[exchange])]
        if security_check.empty:
            raise Exception(f"Check the Tradingsymbol {tradingsymbol}")
        security_id = security_check.iloc[-1]['SEM_SMST_SECURITY_ID']
        return security_id

    def get_trading_symbol(self, token):
        token = int(token)
        instrument_df = self.instrument_df.copy()
        security_check = instrument_df[((instrument_df['SEM_SMST_SECURITY_ID'] == token))]
        if security_check.empty:
            raise Exception(f"Check the token {token}")
        security_tsym = security_check.iloc[-1]['SEM_CUSTOM_SYMBOL']
        return security_tsym

    def get_expiry_from_tsym(self, tsym: str):
        instrument_df = self.instrument_df.copy()
        security_check = instrument_df[((instrument_df['SEM_CUSTOM_SYMBOL'] == tsym))]
        if security_check.empty:
            raise Exception(f"Check the tsym {tsym}")
        expiry = security_check.iloc[-1]['SEM_EXPIRY_DATE']
        return pd.to_datetime(expiry, format='%Y-%m-%d %H:%M:%S')

    def get_token(self, tsym: str):
        instrument_df = self.instrument_df.copy()

        security_check = instrument_df[((instrument_df['SEM_CUSTOM_SYMBOL'] == tsym))]
        if security_check.empty:
            raise Exception("Check the tsym")
        security_token = security_check.iloc[-1]['SEM_SMST_SECURITY_ID']
        return security_token

    def get_balance(self):
        try:
            response = self.dhan_api.get_fund_limits()
            if response['status'] != 'failure':
                balance = float(response['data']['availabelBalance'])
                return balance
            else:
                raise Exception(response)
        except Exception as e:
            print(f"Error at Gettting balance as {e}")
            logger.exception(f"Error at Gettting balance as {e}")
            return 0


    def getPnl(self):
        positions = self.get_positions()
        if positions.empty:
            return 0

        pnl = positions['realizedProfit'].sum() + positions['unrealizedProfit'].sum()
        return pnl

    def getTradeCount(self):
        df = self.get_trade_book()

        if isinstance(df, dict):
            logger.error(f"error getting trade book info: {df}")
            return 0

        if df.empty:
            return 0

        trades = df[df['orderStatus'] == 'TRADED']
        trade_count = 0
        buy_qty = 0
        sell_qty = 0


        # Parse through DataFrame rows
        for index, row in trades.iterrows():
            if row['transactionType'] == 'BUY':
                buy_qty += row['filledQty']
            elif row['transactionType'] == 'SELL':
                sell_qty += row['filledQty']

            # Check if total buy qty is equal to total sell qty
            if buy_qty == sell_qty:
                trade_count += 1
        logger.info(f"trade count: {trade_count}")
        return trade_count

    def getProductType(self, product):
        prd = ''
        if product == 'I':
            prd = "INTRADAY"
        if product == 'M':
            prd = "MARGIN"
        if product == 'C':
            prd = "CNC"
        if product == 'F':
            prd = "MTF"
        if product == 'V':
            prd = "CO"
        if product == 'B':
            prd = "BO"
        return prd


    def get_order_detail(self, orderid: str, debug="NO") -> dict:
        try:
            if orderid is None:
                raise Exception('Check the order id, Error as None')
            orderid = str(orderid)
            time.sleep(1)
            response = self.dhan_api.get_order_by_id(orderid)
            if debug.upper() == "YES":
                print(response)
            if response['status'] == 'success':
                return response['data'][0]
            else:
                raise Exception(response)
        except Exception as e:
            print(f"Error at getting order details as {e}")
            return {
                'status': 'failure',
                'remarks': str(e),
                'data': response,
            }


    def get_positions(self, debug="NO"):
        try:
            time.sleep(1)
            response = self.dhan_api.get_positions()
            if debug.upper() == "YES":
                print(response)
            if response['status'] == 'success':
                return pd.DataFrame(response['data'])
            else:
                raise Exception(response)
        except Exception as e:
            print(f"Error at getting Positions as {e}")
            return {
                'status': 'failure',
                'remarks': str(e),
                'data': response,
            }
    def get_orderbook(self, debug="NO"):
        try:
            time.sleep(1)
            response = self.dhan_api.get_order_list()
            if debug.upper() == "YES":
                print(response)
            if response['status'] == 'success':
                return pd.DataFrame(response['data'])
            else:
                raise Exception(response)
        except Exception as e:
            print(f"Error at get_orderbook as {e}")
            return {
                'status': 'failure',
                'remarks': str(e),
                'data': response,
            }

    def get_trade_book(self, debug="NO"):
        try:
            response = self.dhan_api.get_order_list()
            if debug.upper() == "YES":
                print(response)
            if response['status'] == 'success':
                return pd.DataFrame(response['data'])
            else:
                raise Exception(response)
        except Exception as e:
            print(f"Error at get_trade_book as {e}")
            return {
                'status': 'failure',
                'remarks': str(e),
                'data': response,
            }

    def get_monthly_expiry(self, security_id: str, exchange_segment: str, index=0):
        try:
            response = self.dhan_api.expiry_list(under_security_id=int(security_id),
                                                 under_exchange_segment=exchange_segment)
            if response['status'] == 'success':
                expiries = list(map(lambda x: datetime.strptime(x, "%Y-%m-%d"), response['data']['data']))
                latest_per_month = {}
                for dt in expiries:
                    key = (dt.year, dt.month)
                    latest_per_month[key] = max([dt, latest_per_month.get(key, dt)], key=lambda x: x)

                # Filter input list with lambda to restore order
                expiries = list(filter(lambda dt: latest_per_month[(dt.year, dt.month)] == dt, expiries))

                expiry = expiries[index]
                if datetime.now().date() == expiry.date():
                    return expiries[index + 1]
                return expiries[index]
            else:
                raise Exception(response)
        except Exception as e:
            print(f"Exception at getting Expiry list as {e}")
            return list()



    def get_expiries(self, security_id:str, exchange_segment:str, index = 0):
        try:
            response = self.dhan_api.expiry_list(under_security_id=int(security_id),
                                                under_exchange_segment=exchange_segment)
            if response['status'] == 'success':
                expiries =  list(map(lambda x: datetime.strptime(x, "%Y-%m-%d"), response['data']['data'])) 
                expiry = expiries[index]
                if datetime.now().date() == expiry.date():
                    return expiries[index + 1]
                return expiries[index]
            else:
                raise Exception(response)
        except Exception as e:
            print(f"Exception at getting Expiry list as {e}")
            return list()
        