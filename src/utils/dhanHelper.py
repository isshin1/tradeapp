# from conf.config import dhan_api
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
            time.sleep(6)  # Increased wait time

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