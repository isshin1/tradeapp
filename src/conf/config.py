import yaml
from datetime import datetime
# from Dhan_Tradehull import Tradehull
from Dependencies.Dhan_Tradehull.Dhan_Tradehull import Tradehull
from utils.shoonyaApiHelper import ShoonyaApiPy
import pyotp
import logging
from utils.misc import Misc
import glob, os, sys
from services.alerts import Alerts
import requests
date_str = str(datetime.now().today().date())
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
feed_folder = BASE_DIR + '/data/feed/' + date_str.split('-')[0] + '/' + date_str.split('-')[1] + '/'
log_folder = BASE_DIR + '/data/logs/' + date_str.split('-')[0] + '/' + date_str.split('-')[1] + '/'
order_folder = BASE_DIR + '/data/orderData/' + date_str.split('-')[0] + '/' + date_str.split('-')[1] + '/'
position_folder = BASE_DIR + '/data/positionData/' + date_str.split('-')[0] + '/' + date_str.split('-')[1] + '/'

os.makedirs(feed_folder, exist_ok=True)
os.makedirs(log_folder, exist_ok=True)
os.makedirs(order_folder, exist_ok=True)
os.makedirs(position_folder, exist_ok=True)

if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
print(sys.path)

misc = Misc(BASE_DIR)
# This points to src/
# CONFIG_PATH = os.path.join(BASE_DIR, 'config.yaml')

with open(BASE_DIR+'/conf/config.yaml', 'r') as file:
    config = yaml.safe_load(file)


client_id = config['dhan']['client_id']
access_token = config['dhan']['access_token']
whatsapp_api_key = config['whatsapp']['api_key']

alert = Alerts(whatsapp_api_key)
# alert.send_message("trading session started")


# Get logging level from conf
log_level_str = config.get('logging', {}).get('level', 'INFO')
log_level = getattr(logging, log_level_str.upper(), logging.INFO)



def checkTokenValidity(token):
    url = 'https://api.dhan.co/v2/profile'
    headers = {
        'access-token': token # Replace with actual JWT
    }

    response = requests.get(url, headers=headers)
    res = response.json()
    if 'errorType' in res:
        print("Token is invalid")
        alert.send_message(res['errorMessage'])
        exit(1)
    print(response.status_code)
    print(response.json())  # or response.text if not JSON



nifty_fut_token = 0
try:
    # dhan = dhanhq(client_id, acces_token)
    checkTokenValidity(access_token)

    dhan_api = Tradehull(client_id, access_token, log_level, BASE_DIR)
    logger = dhan_api.logger
    shoonya_api = ShoonyaApiPy()
    # api.logout()
    cred = config['shoonya']
    totp = pyotp.TOTP(cred['totp_key']).now()
    ret = shoonya_api.login(userid = cred['user'], password = cred['pwd'], twoFA=totp,
                    vendor_code=cred['vc'], api_secret=cred['api_key'], imei=cred['imei'])

    nifty_monthly_expiry = misc.get_nse_monthly_expiry("NIFTY", 0)
    if nifty_monthly_expiry.date() < datetime.now().date():
        logger.error("wrong csv file, redownload them")
        for file in glob.glob(os.path.join("Dependencies", "*.csv")):
            os.remove(file)
            print(f"Deleted: {file}")

        raise Exception("wrong csv file, restart app")

    nifty_fut_symbol = "NIFTY" + datetime.strftime(nifty_monthly_expiry, "%d%b%y").upper() + "F"
    nifty_fut_token = misc.getToken(nifty_fut_symbol)
    target1, target2 = config['intraday']['indexes'][0]['targets']
    logger.info(f"default targets are {target1} and {target2}")

except Exception as err :
    print(f"encountered error on logging in {err}")
    alert.send_message(err)
    exit(1)

ltps = dict()


