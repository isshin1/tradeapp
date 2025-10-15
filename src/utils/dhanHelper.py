# from conf.config import dhan_api
from typing import Tuple, Dict

from conf.logging_config import logger
import requests
import os, sys, time
from conf.config import BASE_DIR
import pandas as pd
import traceback
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from urllib.parse import urlparse, parse_qs
import time
import pyotp  # for TOTP generation
from datetime import datetime

from urllib.parse import quote_plus
import random
from urllib.parse import urlparse, parse_qs
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import pad, unpad
import base64
import json
import pyotp
import yaml

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
        time.sleep(1)
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

        trades = trades[['exchangeTime', 'transactionType', 'filledQty']][::-1]
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

    def order_report(self) -> Tuple[Dict, Dict]:
        '''
        If watchlist has more than two stock, using order_report, get the order status and order execution price
        order_report()
        '''
        try:
            order_details = dict()
            order_exe_price = dict()
            time.sleep(1)
            status_df = self.dhan_api.get_order_list()["data"]
            status_df = pd.DataFrame(status_df)
            if not status_df.empty:
                status_df.set_index('orderId', inplace=True)
                order_details = status_df['orderStatus'].to_dict()
                order_exe_price = status_df['averageTradedPrice'].to_dict()

            return order_details, order_exe_price
        except Exception as e:
            self.logger.exception(f"Exception in getting order report as {e}")
            return dict(), dict()

    def cancel_all_orders(self) -> dict:
        try:
            order_details = dict()
            product_detail = {'MIS': self.dhan_api.INTRA, 'MARGIN': self.dhan_api.MARGIN, 'MTF': self.dhan_api.MTF,
                              'CO': self.dhan_api.CO, 'BO': self.dhan_api.BO, 'CNC': self.dhan_api.CNC}
            product = product_detail['MIS']
            time.sleep(1)
            data = self.dhan_api.get_order_list()["data"]
            if data is None or len(data) == 0:
                return order_details
            orders = pd.DataFrame(data)
            if orders.empty:
                return order_details
            trigger_pending_orders = orders.loc[
                (orders['orderStatus'] == 'PENDING') & (orders['productType'] == product)]
            open_orders = orders.loc[(orders['orderStatus'] == 'TRANSIT') & (orders['productType'] == product)]
            for index, row in trigger_pending_orders.iterrows():
                response = self.dhan_api.cancel_order(row['orderId'])

            for index, row in open_orders.iterrows():
                response = self.dhan_api.cancel_order(row['orderId'])
            position_dict = self.dhan_api.get_positions()["data"]
            positions_df = pd.DataFrame(position_dict)
            if positions_df.empty:
                return order_details
            positions_df['netQty'] = positions_df['netQty'].astype(int)
            bought = positions_df.loc[(positions_df['netQty'] > 0) & (positions_df["productType"] == product)]
            sold = positions_df.loc[(positions_df['netQty'] < 0) & (positions_df['productType'] == product)]

            for index, row in bought.iterrows():
                qty = int(row["netQty"])
                order = self.dhan_api.place_order(security_id=str(row["securityId"]),
                                              exchange_segment=row["exchangeSegment"],
                                              transaction_type=self.dhan_api.SELL, quantity=qty,
                                              order_type=self.dhan_api.MARKET, product_type=row["productType"], price=0,
                                              trigger_price=0)

                tradingsymbol = row['tradingSymbol']
                sell_order_id = order["data"]["orderId"]
                order_details[tradingsymbol] = dict({'orderid': sell_order_id, 'price': 0})
                time.sleep(0.5)

            for index, row in sold.iterrows():
                qty = int(row["netQty"]) * -1
                order = self.dhan_api.place_order(security_id=str(row["securityId"]),
                                              exchange_segment=row["exchangeSegment"],
                                              transaction_type=self.dhan_api.BUY, quantity=qty,
                                              order_type=self.dhan_api.MARKET, product_type=row["productType"], price=0,
                                              trigger_price=0)
                tradingsymbol = row['tradingSymbol']
                buy_order_id = order["data"]["orderId"]
                order_details[tradingsymbol] = dict({'orderid': buy_order_id, 'price': 0})
                time.sleep(1)
            if len(order_details) != 0:
                _, order_price = self.order_report()
                for key, value in order_details.items():
                    orderid = str(value['orderid'])
                    if orderid in order_price:
                        order_details[key]['price'] = order_price[orderid]
            return order_details
        except Exception as e:
            print(e)
            print("problem close all trades")
            logger.exception("problem close all trades")
            traceback.print_exc()

    def kill_switch(self, action):
        try:
            active = {'ON': 'ACTIVATE', 'OFF': 'DEACTIVATE'}
            current_action = active[action.upper()]

            killswitch_response = self.dhan_api.kill_switch(current_action)
            if 'killSwitchStatus' in killswitch_response['data'].keys():
                return killswitch_response['data']['killSwitchStatus']
            else:
                return killswitch_response
        except Exception as e:
            logger.exception(f"Error at Kill switch as {e}")


class DhanAuthAutomation:
    def __init__(self, headless=True):
        """Initialize the browser with headless option"""
        chrome_options = Options()

        if headless:
            chrome_options.add_argument('--headless=new')

        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])

        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 20)

    def wait_for_next_minute_if_needed(self, threshold_seconds=5):
        """
        Wait for the next minute if we're close to the current minute ending.
        This ensures TOTP has maximum validity time.

        Args:
            threshold_seconds (int): If remaining seconds in current minute
                                    is less than this, wait for next minute
        """
        now = datetime.now()
        seconds_remaining = 60 - now.second

        if seconds_remaining < threshold_seconds:
            wait_time = seconds_remaining + 1
            print(f"Current time: {now.strftime('%H:%M:%S')}")
            print(f"Only {seconds_remaining}s remaining in current minute. Waiting {wait_time}s for fresh TOTP...")
            time.sleep(wait_time)
            print(f"New time: {datetime.now().strftime('%H:%M:%S')}")

    def paste_code_to_first_field(self, code, field_selector=None, distribute=True):
        """
        Paste a code (TOTP or PIN) into the first input field

        Args:
            code (str): The code to paste (6 digits)
            field_selector (str): Optional CSS selector for the first field
            distribute (bool): Whether to distribute code across multiple fields
        """
        try:
            # Find all visible input fields
            if field_selector:
                first_input = self.driver.find_element(By.CSS_SELECTOR, field_selector)
            else:
                inputs = self.driver.find_elements(By.CSS_SELECTOR,
                                                   "input[type='text'], input[type='tel'], input[type='password'], input[maxlength='1']")
                visible_inputs = [inp for inp in inputs if inp.is_displayed()]
                if not visible_inputs:
                    raise Exception("No visible input fields found")
                first_input = visible_inputs[0]

            # Click on the first input to focus
            first_input.click()
            time.sleep(0.5)

            # Distribute the code across input fields immediately if requested
            if distribute:
                self.driver.execute_script(f"""
                    const code = '{code}';
                    const inputs = Array.from(document.querySelectorAll('input[type="text"], input[type="tel"], input[type="password"], input[maxlength="1"]'))
                        .filter(inp => inp.offsetParent !== null); // Only visible inputs

                    if (inputs.length >= code.length) {{
                        // Distribute across multiple inputs
                        for (let i = 0; i < code.length && i < inputs.length; i++) {{
                            inputs[i].value = code[i];
                            inputs[i].dispatchEvent(new Event('input', {{ bubbles: true }}));
                            inputs[i].dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                        inputs[code.length - 1].dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    }} else if (inputs.length > 0) {{
                        // Put entire code in first input
                        inputs[0].value = code;
                        inputs[0].dispatchEvent(new Event('input', {{ bubbles: true }}));
                        inputs[0].dispatchEvent(new Event('change', {{ bubbles: true }}));
                        inputs[0].dispatchEvent(new Event('blur', {{ bubbles: true }}));
                    }}
                """)
            else:
                # Just fill the first input
                self.driver.execute_script(f"""
                    const input = arguments[0];
                    input.value = '{code}';
                    input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    input.dispatchEvent(new Event('blur', {{ bubbles: true }}));
                """, first_input)

            print(
                f"Code {'distributed' if distribute else 'pasted'} successfully: {code} {datetime.now().strftime('%H:%M:%S')}")

        except Exception as e:
            print(f"Error pasting code: {e}")
            raise

    def get_auth_token(self, login_url, mobile_number, totp_secret, pin):
        """
        Automate the Dhan authentication flow

        Args:
            login_url (str): The initial login URL
            mobile_number (str): Your mobile number
            totp_secret (str): Your TOTP secret key for generating OTP
            pin (str): Your 6-digit PIN

        Returns:
            str: The tokenId extracted from the redirect URL
        """
        try:
            # Step 1: Open the login URL
            print(f"Opening login URL: {login_url}")
            self.driver.get(login_url)
            time.sleep(2)

            # Step 2: Enter mobile number
            print("Entering mobile number...")
            # Wait for Angular to load and form to be ready
            time.sleep(1)

            # Try multiple selectors for the mobile input field
            mobile_input = None
            selectors = [
                "input[placeholder='Enter mobile number']",
                "input[formcontrolname='mobileNumber']",
                "input[ng-reflect-name='mobileNumber']",
                "input[type='tel']",
                "input[placeholder*='mobile' i]"
            ]

            for selector in selectors:
                try:
                    mobile_input = self.driver.find_element(By.CSS_SELECTOR, selector)
                    if mobile_input:
                        break
                except:
                    continue

            if not mobile_input:
                mobile_input = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "input"))
                )

            # Click to focus, then clear and enter
            mobile_input.click()
            time.sleep(1)
            mobile_input.clear()
            mobile_input.send_keys(mobile_number)

            # Trigger Angular form validation by clicking outside or pressing Tab
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('input', { bubbles: true }));",
                                       mobile_input)
            self.driver.execute_script("arguments[0].dispatchEvent(new Event('blur', { bubbles: true }));",
                                       mobile_input)
            time.sleep(1)

            # Click Proceed button
            proceed_button = self.wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'Proceed') or contains(., 'Proceed')]"))
            )
            # Scroll into view if needed
            self.driver.execute_script("arguments[0].scrollIntoView(true);", proceed_button)
            # time.sleep(2)
            proceed_button.click()
            print("Mobile number submitted")
            time.sleep(3)  # Wait for navigation to TOTP page

            # Step 3: Enter TOTP with retry logic
            print("\n--- TOTP Entry ---")

            # Verify we're on the TOTP page
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//*[contains(text(), 'Verify with TOTP')]"))
                )
                print("✓ Confirmed on TOTP verification page")
            except:
                print("⚠ Could not confirm TOTP page text, proceeding anyway...")

            # Wait for next minute if needed
            self.wait_for_next_minute_if_needed(threshold_seconds=5)

            # Generate fresh TOTP
            totp = pyotp.TOTP(totp_secret)
            otp_code = totp.now()
            print(f"Generated TOTP: {otp_code} at {datetime.now().strftime('%H:%M:%S')}")

            # Clear any existing values first
            try:
                self.driver.execute_script("""
                    const inputs = Array.from(document.querySelectorAll('input[type="text"], input[type="tel"], input[maxlength="1"]'))
                        .filter(inp => inp.offsetParent !== null);
                    inputs.forEach(inp => {
                        inp.value = '';
                        inp.dispatchEvent(new Event('input', { bubbles: true }));
                    });
                """)
                time.sleep(0.3)  # Brief pause after clearing
            except:
                pass

            # Paste TOTP ONCE
            self.paste_code_to_first_field(otp_code, distribute=True)

            # Wait for auto-submission
            print(f"Waiting for TOTP auto-submission... {datetime.now().strftime('%H:%M:%S')}")
            time.sleep(3)  # Increased wait time
            print("check if proceed button exists")
            try:
                proceed_button = self.wait.until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//button[contains(text(), 'Proceed') or contains(., 'Proceed')]"))
                )
                # Scroll into view if needed
                self.driver.execute_script("arguments[0].scrollIntoView(true);", proceed_button)
                proceed_button.click()
                print("proceed button clicked")
                time.sleep(3)
            except:
                # Proceed button doesn't exist, continue without clicking
                pass

            # Verify we've moved past TOTP page
            totp_success = False
            try:
                still_on_totp_page = self.driver.find_elements(By.XPATH, "//*[contains(text(), 'Verify with TOTP')]")

                if still_on_totp_page and len(still_on_totp_page) > 0:
                    print("✗ TOTP was rejected, still on verification page")

                    # Check for error message
                    try:
                        error_msg = self.driver.find_element(By.XPATH,
                                                             "//*[contains(text(), 'Invalid') or contains(text(), 'incorrect') or contains(text(), 'expired')]")
                        print(f"Error message: {error_msg.text}")
                    except:
                        pass

                    raise Exception("TOTP verification failed")
                else:
                    print(f"✓ TOTP accepted! Moved to next page at {datetime.now().strftime('%H:%M:%S')}")
                    totp_success = True

            except Exception as e:
                if "TOTP verification failed" in str(e):
                    raise
                # If we can't find the TOTP text, we've likely moved on
                print("✓ Appears to have moved past TOTP page")

            if not totp_success:
                raise Exception("Failed to complete TOTP verification")

            # Step 4: Enter PIN
            print("\n--- PIN Entry ---")

            # Wait for PIN page to fully load
            print("Waiting for PIN entry page to load...")
            time.sleep(3)

            # Verify we're on the PIN page by checking for PIN-related text or elements
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH,
                                                    "//*[contains(text(), 'PIN') or contains(text(), 'pin') or contains(text(), 'Enter your PIN')]"))
                )
                print("✓ Confirmed on PIN entry page")
            except:
                print("⚠ Could not confirm PIN page text, proceeding anyway...")

            time.sleep(2)  # Additional buffer to ensure page is stable

            # Paste PIN - distribute immediately across fields
            self.paste_code_to_first_field(pin, distribute=True)

            # Wait for auto-submission (no button click needed)
            print("Waiting for PIN auto-submission...")
            time.sleep(2)

            # Step 5: Wait for redirect and extract tokenId
            print("Waiting for redirect...")
            self.wait.until(
                lambda driver: 'token' in driver.current_url.lower() or len(driver.current_url) > len(login_url))
            time.sleep(2)

            redirect_url = self.driver.current_url
            print(f"Redirected to: {redirect_url}")

            # Extract tokenId from URL
            parsed_url = urlparse(redirect_url)
            query_params = parse_qs(parsed_url.query)

            # Try different parameter names
            token_id = None
            for param_name in ['tokenId', 'token_id', 'token', 'accessToken', 'access_token']:
                if param_name in query_params:
                    token_id = query_params[param_name][0]
                    break

            if token_id:
                print(f"Successfully extracted tokenId: {token_id}")
                return token_id
            else:
                print("Warning: tokenId not found in URL parameters")
                print(f"Available parameters: {list(query_params.keys())}")
                return None

        except Exception as e:
            print(f"Error during authentication: {str(e)}")
            # Take screenshot for debugging
            self.driver.save_screenshot('error_screenshot.png')
            raise

    def close(self):
        """Close the browser"""
        if self.driver:
            self.driver.quit()
            print("Browser closed")



# Constants from the JavaScript code analysis
SALT = bytes.fromhex("498960e491150a0fc0f21822a147fd62")
IV = bytes.fromhex("320ef7705d1030f0a1a55b3dcf676cb8")
PASSPHRASE = "DHAN"
KEY_SIZE = 16  # 128 bits
ITERATIONS = 1000

# --- Configuration ---
TOKEN_URL = "https://partner-login.dhan.co/jwt/token"
LOGIN_URL = "https://partner-login.dhan.co/loginV2/login"
TOTP_URL = "https://partner-login.dhan.co/dhanhq/validateTOTP"
SIMPLIFIED_LOGIN_URL = "https://partner-login.dhan.co/loginV2/simplifiedLogin"
CONSUME_CONSENT_URL = "https://partner-login.dhan.co/loginV2/consentAppConsume"
ACCESS_TOKEN_URL = "https://auth.dhan.co/app/consumeApp-consent"


def generate_key():
    """Derives the encryption key using PBKDF2."""
    return PBKDF2(PASSPHRASE, SALT, dkLen=KEY_SIZE, count=ITERATIONS)


def encrypt(data_dict):
    """
    Encrypts a dictionary using AES CBC, matching the logic from the Dhan website.

    Args:
        data_dict: The dictionary to encrypt.

    Returns:
        A Base64 encoded string of the encrypted data.
    """
    try:
        key = generate_key()
        cipher = AES.new(key, AES.MODE_CBC, IV)
        plaintext = json.dumps(data_dict, separators=(',', ':')).encode('utf-8')
        padded_plaintext = pad(plaintext, AES.block_size)
        ciphertext = cipher.encrypt(padded_plaintext)
        return base64.b64encode(ciphertext).decode('utf-8')
    except Exception as e:
        print(f"An error occurred during encryption: {e}")
        return None


def decrypt(encrypted_base64_string):
    """
    Decrypts a Base64 encoded AES CBC string, matching the logic from the Dhan website.

    Args:
        encrypted_base64_string: The Base64 encoded string to decrypt.

    Returns:
        The decrypted dictionary.
    """
    try:
        key = generate_key()
        cipher = AES.new(key, AES.MODE_CBC, IV)

        # Decode the Base64 string to get the ciphertext
        ciphertext = base64.b64decode(encrypted_base64_string)

        # Decrypt and unpad the data
        decrypted_padded = cipher.decrypt(ciphertext)
        decrypted = unpad(decrypted_padded, AES.block_size)

        # Decode from bytes to string and parse JSON
        return json.loads(decrypted.decode('utf-8'))

    except (ValueError, KeyError) as e:
        print(f"An error occurred during decryption (likely padding error or invalid key): {e}")
        return None
    except Exception as e:
        print(f"An error occurred during decryption: {e}")
        return None


def generate_device_id():
    """Generate device ID exactly like Dhan's getDeviceInfo() function"""
    # Simulating browser characteristics
    mime_types_length = 4
    user_agent_digits = "537361"
    plugins_length = 5
    screen_height = 1080
    screen_width = 1920
    pixel_depth = 24
    random_number = random.randint(0, 999999)

    # Concatenate all values as strings (like JavaScript does)
    device_id = str(mime_types_length)
    device_id += user_agent_digits
    device_id += str(plugins_length)
    device_id += str(screen_height)
    device_id += str(screen_width)
    device_id += str(pixel_depth)
    device_id += str(random_number)

    print(f"generated device id is {device_id}")
    return device_id


def get_base_headers(consent_app_id):
    """Returns base headers used across all requests"""
    return {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Origin': 'https://partner-login.dhan.co',
        'Referer': f'https://partner-login.dhan.co/?consentAppId={consent_app_id}',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
    }


def get_jwt_token(session, user_id, device_id, consent_app_id):
    """
    Fetches the JWT token by sending a URL-encoded JSON payload,
    mimicking the provided curl command.
    """
    print("Requesting JWT Token...")

    payload = {
        "user_id": user_id,
        "pass": None,
        "imei_no": device_id,
        "web_version": "Chrome Browser",
        "role": "Admin",
        "app_version": "v1.0.0.10",
        "app_id": "DH_WEB",
        "source": "P"
    }

    # Convert dict to JSON string, then URL-encode the whole string
    request_body = quote_plus(json.dumps(payload, separators=(',', ':')))

    headers = get_base_headers(consent_app_id)

    try:
        # The initial GET request helps in setting up necessary cookies
        session.get(f"https://partner-login.dhan.co/?consentAppId={consent_app_id}")

        print("\nSending POST request to:", TOKEN_URL)
        print("Headers:", json.dumps(headers, indent=2))
        print("Raw Body:", request_body)

        response = session.post(TOKEN_URL, headers=headers, data=request_body)
        response.raise_for_status()

        jwt_token = response.text
        print("\n--- SUCCESS ---")
        print("Received JWT Token:", jwt_token)
        return jwt_token

    except requests.exceptions.RequestException as e:
        print(f"\n--- ERROR ---")
        print(f"Error getting JWT token: {e}")
        if e.response is not None:
            print("Status Code:", e.response.status_code)
            print("Response Body:", e.response.text)
        return None


def login(session, user_id, device_id, jwt_token, consent_app_id):
    """
    Step 2: Performs login using the JWT, sending a raw, encrypted payload.
    """
    print("\n--- Step 2: Performing Login ---")

    payload = {
        "user_id": user_id,
        "pass": None,
        "imei_no": device_id,
        "web_version": "Chrome Browser",
        "role": "Admin",
        "app_version": "v1.0.0.10",
        "app_id": "DH_WEB",
        "source": "P",
        "askpass": True
    }

    encrypted_payload_str = encrypt(payload)
    if not encrypted_payload_str:
        print("Encryption failed.")
        return

    # As per the curl command, the raw body is the encrypted string,
    # wrapped in quotes, and then URL-encoded.
    request_body = quote_plus(f'"{encrypted_payload_str}"')

    headers = get_base_headers(consent_app_id)
    headers['Authorisation'] = f'Token {jwt_token}'

    try:
        response = session.post(LOGIN_URL, headers=headers, data=request_body)
        response.raise_for_status()

        print("Login request sent successfully.")

        encrypted_response_data = response.json().get("data")
        print("Raw Encrypted Response Data:", encrypted_response_data)

        decrypted_response = decrypt(encrypted_response_data)
        if "status" in decrypted_response and decrypted_response["status"] == "success":
            print("\n--- SUCCESS ---")
            print("Decrypted Login Response:", json.dumps(decrypted_response, indent=2))
            return decrypted_response["data"][0]["token_id"]

    except requests.exceptions.RequestException as e:
        print(f"\n--- ERROR ---")
        print(f"Error during login: {e}")
        if e.response is not None:
            print("Status Code:", e.response.status_code)
            print("Response Body:", e.response.text)


def validate_totp(session, token_id, totp_key, device_id, user_id, consent_app_id, jwt_token):
    totp = pyotp.TOTP(totp_key)
    otp_code = totp.now()

    payload = {
        "otp": otp_code, "device_id": device_id, "entity_id": user_id,
        "token_id": token_id, "web_version": "Chrome Browser", "source": "P"
    }
    encrypted_payload = encrypt(payload)
    request_body = quote_plus(f'"{encrypted_payload}"')
    headers = get_base_headers(consent_app_id)
    headers['Authorisation'] = f'Token {jwt_token}'

    try:
        response = session.post(TOTP_URL, headers=headers, data=request_body)
        response.raise_for_status()
        encrypted_data = response.json().get("data")
        decrypted_data = decrypt(encrypted_data)
        print("TOTP validation request successful.")
        print("Decrypted TOTP Response:", json.dumps(decrypted_data, indent=2))
        return decrypted_data
    except requests.exceptions.RequestException as e:
        print(f"Error in Step 3: {e}")
        return None


def simplified_login(session, token_id, pin, consent_app_id, user_id, jwt_token):
    payload = {
        "user_id": user_id,
        "token_id": token_id,
        "pass_type": "OP",
        "salt": "nahd",
        "pin": pin,
        "web_version": "Chrome Browser",
        "source": "P",
        "consent_id": consent_app_id
    }
    encrypted_payload = encrypt(payload)
    request_body = quote_plus(f'"{encrypted_payload}"')
    headers = get_base_headers(consent_app_id)
    headers['Authorisation'] = f'Token {jwt_token}'

    try:
        response = session.post(SIMPLIFIED_LOGIN_URL, headers=headers, data=request_body)
        response.raise_for_status()
        encrypted_data = response.json().get("data")
        decrypted_data = decrypt(encrypted_data)
        print("simplified login request successful.")
        print("simplified Login Response:", json.dumps(decrypted_data, indent=2))

        return decrypted_data
    except requests.exceptions.RequestException as e:
        print(f"Error in Step 3: {e}")
        return None


def consume_concent(session, consent_app_id, client_id, jwt_token):
    payload = {
        "consentId": consent_app_id,
        "client_id": client_id
    }
    encrypted_payload = encrypt(payload)
    request_body = quote_plus(f'"{encrypted_payload}"')
    headers = get_base_headers(consent_app_id)
    headers['Authorisation'] = f'Token {jwt_token}'

    try:
        response = session.post(CONSUME_CONSENT_URL, headers=headers, data=request_body, allow_redirects=False)
        response.raise_for_status()
        encrypted_data = response.json().get("data")
        decrypted_data = decrypt(encrypted_data)
        print("consent consumption request successful.")
        print("consent consumption Response:", json.dumps(decrypted_data, indent=2))

        # return decrypted_data
        redirect_url = decrypted_data["data"]["redirectUrl"]
        parsed_url = urlparse(redirect_url)
        query_params = parse_qs(parsed_url.query)

        token_id = query_params.get("tokenId", [None])[0]

        return token_id

    except requests.exceptions.RequestException as e:
        print(f"Error in Step 3: {e}")
        return None


def extract_access_token(token_id, app_id, app_secret):
    url = ACCESS_TOKEN_URL + f"?tokenId={token_id}"
    headers = {
        "app_id": app_id,
        "app_secret": app_secret
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()  # raise error if request failed
    data = response.json()
    # Extract access token
    access_token = data.get("accessToken")
    print("Access Token:", access_token)
    return access_token


def get_concent_app_id(client_id, app_id, app_secret):
    url = f"https://auth.dhan.co/app/generate-consent?client_id={client_id}"

    headers = {
        "app_id": app_id,
        "app_secret": app_secret
    }

    response = requests.post(url, headers=headers)
    response.raise_for_status()  # raise error if request fails

    data = response.json()

    consent_app_id = data.get("consentAppId")
    print(f"generated concent id is {consent_app_id} ")
    return consent_app_id


def get_access_token(cred):
    CLIENT_ID = str(cred['client_id'])
    USER_ID = str(cred['phone_number'])
    app_id = str(cred['app_id'])
    app_secret = cred['app_secret']
    TOTP_KEY = cred['totp_secret']
    PIN = str(cred['pin'])

    DEVICE_ID = generate_device_id()
    CONSENT_APP_ID = get_concent_app_id(CLIENT_ID, app_id, app_secret)

    with requests.Session() as s:
        # Step 1: Get the JWT token
        token = get_jwt_token(s, USER_ID, DEVICE_ID, CONSENT_APP_ID)

        if token:
            # Step 2: Use the token to perform the login
            token_id = login(s, USER_ID, DEVICE_ID, token, CONSENT_APP_ID)
            validate_totp(s, token_id, TOTP_KEY, DEVICE_ID, USER_ID, CONSENT_APP_ID, token)
            simplified_login(s, token_id, PIN, CONSENT_APP_ID, USER_ID, token)
            token_id = consume_concent(s, CONSENT_APP_ID, CLIENT_ID, token)
            access_token = extract_access_token(token_id, app_id, app_secret)
            return access_token
