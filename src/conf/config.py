import yaml
from datetime import datetime
import glob, os, sys



BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_date_folders(date_str=None):
    """Generate folder paths based on date"""
    if date_str is None:
        date_str = str(datetime.now().date())

    year, month = date_str.split('-')[:2]

    return {
        'feed': os.path.join(BASE_DIR, 'data', 'feed', year, month),
        'log': os.path.join(BASE_DIR, 'data', 'logs', year, month),
        'order': os.path.join(BASE_DIR, 'data', 'orderData', year, month),
        'position': os.path.join(BASE_DIR, 'data', 'positionData', year, month)
    }

with open(BASE_DIR+'/conf/config.yaml', 'r') as file:
    config = yaml.safe_load(file)
#
# dhan_web = DhanWebSocketSimple(config)
#
# misc = Misc(BASE_DIR, config)
#
# client_id = config['dhan']['client_id']
# access_token = config['dhan']['access_token']
# whatsapp_api_key = config['whatsapp']['api_key']
#
# alert = Alerts(whatsapp_api_key)
# # alert.send_message("trading session started")
#
#
# # Get logging level from conf
# log_level_str = config.get('logging', {}).get('level', 'INFO')
# log_level = getattr(logging, log_level_str.upper(), logging.INFO)
#
# def checkTokenValidity(token):
#     # from services.riskManagement import RiskManagement
#     # riskManagementobj = RiskManagement()
#     url = 'https://api.dhan.co/v2/profile'
#     headers = {
#         'access-token': token # Replace with actual JWTlogger.
#     }
#
#     response = requests.get(url, headers=headers)
#     res = response.json()
#     if 'errorType' in res:
#         logger.error("Token is invalid")
#         alert.send_message("Dhan api error", res['errorMessage'])
#         raise Exception("Dhan Token is invalid")
#     logger.info(response.status_code)
#     logger.info(response.json())  # or response.text if not JSON
#
#
# DATABASE_URL = config['database']['url']
# db_helper = DBHelper(DATABASE_URL)
# decisionPoints = DecisionPoints(db_helper)
#
#
# nifty_fut_token = 0
# try:
#     # dhan = dhanhq(client_id, acces_token)
#
#     dhan_context = DhanContext(client_id, access_token)
#     dhan_api = dhanhq(dhan_context)
#     # dhan_api = Tradehull(dhan_context, log_level, BASE_DIR)
#     nifty_monthly_expiry = misc.get_nse_monthly_expiry("NIFTY", 0)
#     if nifty_monthly_expiry.date() < datetime.now().date():
#         logger.error("wrong csv file, redownload them")
#         for file in glob.glob(os.path.join("Dependencies", "*.csv")):
#             os.remove(file)
#             print(f"Deleted: {file}")
#
#         raise Exception("wrong csv file, restart app")
#
#     nifty_fut_symbol = "NIFTY" + datetime.strftime(nifty_monthly_expiry, " %b ").upper() + "FUT"
#     # nifty_fut_symbol = "NIFTY SEP FUT"
#
#     # nifty_fut_token = misc.getToken(nifty_fut_symbol)
#     nifty_fut_token = str(dhan_api.get_token(nifty_fut_symbol))
#
#     dhanHelper = DhanHelper(dhan_api)
#     riskManagement = RiskManagement(config, dhan_api, dhanHelper)
#     tradeManager = TradeManager()
#     connection_manager = ConnectionManager()
#
#     tradeManagement =  TradeManagement(config, dhan_api,  tradeManager, nifty_fut_token, riskManagement, dhanHelper, decisionPoints, misc)
#     optionUpdate = OptionUpdate(config, dhan_api, shoonya_api,  misc, tradeManagement, tradeManager, nifty_fut_token, nifty_fut_symbol)
#
#
#     dhanwebsocket = DhanWebsocket(client_id, access_token, tradeManagement )
#     dhanwebsocket.start_dhan_websocket()
#
#     shoonyaWebsocket = ShoonyaWebsocket(config, tradeManagement, tradeManager, shoonya_api, nifty_fut_token, dhan_api, feed_folder, optionUpdate )
#     shoonyaWebsocket.start_shoonya_websocket()
#
#     checkTokenValidity(access_token)
#
#     orderManagement = OrderManagement(dhan_api, shoonya_api , order_folder, nifty_fut_token, riskManagement, tradeManager, decisionPoints, misc)
#     # pihole = Pihole()
#     # pihole.disablePihole()  # disable blocking on startup
#
# except Exception as err :
#     logger.error(f"encountered error on logging in {err}")
#     alert.send_message("enabling killswitch", str(err))
#     # riskManagement.killswitch()
#     exit(1)



