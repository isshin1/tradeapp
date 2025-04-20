import yaml
from datetime import datetime
# from Dhan_Tradehull import Tradehull
from Dependencies.Dhan_Tradehull.Dhan_Tradehull import Tradehull
from utils.shoonyaApiHelper import ShoonyaApiPy
import pyotp
import logging
from utils.misc import misc
import glob, os, sys


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)
print(sys.path)
# This points to src/
# CONFIG_PATH = os.path.join(BASE_DIR, 'config.yaml')

with open(BASE_DIR+'/conf/config.yaml', 'r') as file:
    config = yaml.safe_load(file)

client_id = config['dhan']['client_id']
access_token = config['dhan']['access_token']


# Get logging level from conf
log_level_str = config.get('logging', {}).get('level', 'INFO')
log_level = getattr(logging, log_level_str.upper(), logging.INFO)

nifty_fut_token = 0
try:
    # dhan = dhanhq(client_id, acces_token)
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

except Exception as err :
    print(f"encountered error on logging in {err}")
    exit(1)

ltps = dict()