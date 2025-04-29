#
from conf.config import *
from apscheduler.schedulers.background import BackgroundScheduler
# from utils.misc import misc
# from dateutil.relativedelta import TH, relativedelta

from datetime import datetime, timedelta
import csv, os
import pandas as pd
# import pause
from services.orderManagement import getOrderBook
# %%
# with open('shared_libraries/config.yaml') as f:
#     config = yaml.load(f, Loader=yaml.FullLoader)
#
# shoonya_api = Shoonyashoonya_apiPy()
# # shoonya_api.logout()
# cred = config['shoonya']
# totp = pyotp.TOTP(cred['totp_key']).now()
# ret = shoonya_api.login(userid=cred['user'], password=cred['pwd'], twoFA=totp,
#                 vendor_code=cred['vc'], shoonya_api_secret=cred['shoonya_api_key'], imei=cred['imei'])

# %%
current_date_str = datetime.now().strftime('%Y-%m-%d')
out_folder = config['intraday_candle_recorder']['out_folder']
# log_path = out_folder + '/logs/'
# os.makedirs(log_path, exist_ok=True)

# %%
# log_file = log_path + current_date_str + '.log'
#
# print(f'log file is {log_file}')
# # Create and configure logger
# logger = loggerHelper.setup_logger("general", log_file)
# logger.setLevel(logging.INFO)
# logger.info(f'starting downloading candle data')
# logger.debug(f"output path is {out_path}")

# %%
# download current fno symbols
# indexDict = startup.clean()


# %%
# dump data to csv file
def dump_to_csv(data, out_file):
    # create folder if doesnt exisst
    directory_path = os.path.dirname(out_file)
    os.makedirs(directory_path, exist_ok=True)

    df = pd.DataFrame(data)
    rows = []
    fields = ['time', 'open', 'high', 'low', 'close', 'volume']
    with open(out_file, 'w') as csvfile:
        csvwriter = csv.writer(csvfile)
        csvwriter.writerow(fields)

        for candle in df.itertuples():
            # time = candle.time.split(' ')

            date = candle.time.split(' ')[0]
            time = candle.time.split(' ')[1]
            date = datetime.strptime(date, '%d-%m-%Y').strftime('%Y-%m-%d')
            date = date + ' ' + time

            # break
            # time = time.replace('"','')
            o = candle.into
            h = candle.inth
            l = candle.intl
            c = candle.intc
            volume = candle.v
            # volume = 0
            row = [date, o, h, l, c, volume]
            rows.append(row)

        for row in rows:
            csvwriter.writerow(row)
        logger.info("downloaded: " + out_file)



# %%
def get_bse_expiries_list(symbol, uc, lc, current_expiry):
    df = df = pd.read_csv(bfo_file)
    print(symbol, uc, lc)

    if symbol == 'SENSEX':
        symbol = 'BSXOPT'
    if symbol == 'BANKEX':
        symbol = 'BKXOPT'

    df_ind = df[df.Symbol == symbol]
    df_ind = df_ind[pd.to_datetime(df_ind['Expiry'], format='%d-%b-%Y') == current_expiry]

    # print(df_ind)
    df_exp = df_ind[df_ind['StrikePrice'].between(lc, uc)]
    return df_exp


def get_nse_expiries_list(symbol, uc, lc, current_expiry):
    df = pd.read_csv(misc.nfo_file)
    print(symbol, uc, lc)
    df_ind = df[df.Symbol == symbol]
    df_ind = df_ind[pd.to_datetime(df_ind['Expiry'], format='%d-%b-%Y') == current_expiry]

    # print(df_ind)
    df_exp = df_ind[df_ind['StrikePrice'].between(lc, uc)]
    return df_exp


def get_expiries_list(symbol, exch, uc, lc, current_expiry):
    if exch == 'NSE':
        return get_nse_expiries_list(symbol, uc, lc, current_expiry)
    else:
        return get_bse_expiries_list(symbol, uc, lc, current_expiry)


# %%
def download_weekly_options(symbol, expiries_list, prev_expiry, current_expiry):
    for row in expiries_list.itertuples():
        for interval in range(1, 7, 2):
            ret = shoonya_api.get_time_price_series(exchange=str(row.Exchange), token=str(row.Token),
                                            starttime=prev_expiry.timestamp(), interval=interval)
            ret.reverse()
            out_file = out_folder + '/' + symbol + '/optionData/' + current_expiry.strftime('%Y/%m/%d/') + str(
                interval) + 'm/' + row.TradingSymbol + '.csv'
            dump_to_csv(ret, out_file)


def parse_weekly_options(symbol, exch, token):
    current_expiry = misc.get_weekly_expiry(symbol, exch, download=True)
    #TODO: add all expiries in db and fetch from it
    prev_expiry = current_expiry - timedelta(days=7)
    # prev_expiry = misc.get_previous_expiry(symbol + ' WEEKLY', current_expiry)

    print(symbol, prev_expiry, current_expiry)

    ret = shoonya_api.get_time_price_series(exchange=exch, token=str(token), starttime=prev_expiry.timestamp(),
                                    endtime=current_expiry.timestamp(), interval=240)
    df = pd.DataFrame(ret)
    maxima = float(df['inth'].max())
    minima = float(df['intl'].min())

    uc = int(maxima / 50) * 50 + 510
    lc = int(minima / 50) * 50 - 100

    expiries_list = get_expiries_list(symbol, exch, uc, lc, current_expiry)
    # print(expiries_list)
    download_weekly_options(symbol, expiries_list, prev_expiry , current_expiry)


# %%
def download_monthly_indices(symbol, exch, token):
    current_date = datetime.now()
    start_of_month = datetime(current_date.year, current_date.month, 1)

    for interval in range(1, 7, 2):
        ret = shoonya_api.get_time_price_series(exchange=exch, token=token, starttime=start_of_month.timestamp(),
                                        interval=interval)
        ret.reverse()
        out_file = out_folder + '/' + symbol + '/indexData/' + datetime.now().strftime('%Y/%m/') + str(
            interval) + 'm/' + symbol + '.csv'
        dump_to_csv(ret, out_file)


# %%
def download_monthly_futures(symbol, exch):
    current_expiry = misc.get_monthly_expiry(symbol, exch)
    # TODO: get previous expiries from db
    previous_expiry = current_expiry - timedelta(days=40) # need a way to log previous expiries
    fut_symbol = symbol + current_expiry.strftime('%d%b%y').upper() + "F"

    df = pd.read_csv(misc.nfo_file)
    row = df[df.TradingSymbol == fut_symbol].iloc[0]
    exch = row.Exchange
    token = str(row.Token)
    try:
        for interval in range(1, 7, 2):
            ret = shoonya_api.get_time_price_series(exchange=exch, token=token, starttime=previous_expiry.timestamp(),
                                            interval=interval)
            if ret == None:
                logger.error(f"fut data for {interval}m is empty")
                continue
            ret.reverse()
            out_file = out_folder + '/' + symbol + '/futureData/' + current_expiry.strftime('%Y/%m/') + str(
                interval) + 'm/' + symbol + '_F1.csv'
            dump_to_csv(ret, out_file)

        # if expiry day, download next month data as well
        if current_expiry == datetime.now().date():
            previous_expiry = current_expiry
            current_expiry = misc.get_monthly_expiry(symbol, exch, month=1)
            for interval in range(1, 7, 2):
                ret = shoonya_api.get_time_price_series(exchange=exch, token=token, starttime=previous_expiry.timestamp(),
                                                        interval=interval)
                ret.reverse()
                out_file = out_folder + '/' + symbol + '/futureData/' + current_expiry.strftime('%Y/%m/') + str(
                    interval) + 'm/' + symbol + '_F1.csv'
                dump_to_csv(ret, out_file)
    except Exception as e:
        logger.error(f"Exception in downloading fut data: {e}")

# %%
def parse_indexes():
    indexes = config['intraday']['indexes']
    for index in indexes:
        index_name = index['name']
        token = str(index['token'])
        exch = index['exchange']
        print(index_name, exch, token)
        parse_weekly_options(index_name, exch, token)
        download_monthly_indices(index_name, exch, token)
        if exch != 'BSE':
            download_monthly_futures(index_name, exch)
    logger.info("candle download finished")

# parse_indexes()
def downloadCheck(force=False):
    symbol = nifty_fut_symbol
    year = '20' + symbol[-3:-1]
    month = datetime.strptime(symbol[-6:-3], '%b').strftime('%m').zfill(2)
    fut_file = out_folder + '/NIFTY/futureData/' + year + '/' + month + '/3m/NIFTY_F1.csv'

    download = True
    if os.path.exists(fut_file):
        df = pd.read_csv(fut_file)
        df['time'] = pd.to_datetime(df['time'])
        # today_date = datetime.today().date()
        # has_today = df['time'].dt.date.eq(today_date).any()
        # if has_today and not force:
        #     download = False
        today_end_time = datetime.today().replace(hour=15, minute=27, second=0, microsecond=0)
        has_today = df.iloc[-1]['time'] == today_end_time
        if has_today and not force:
            download = False

    if download or force:
        logger.info("Downloading candlestick data now")
        parse_indexes()
        getOrderBook()
        if os.path.exists('/.dockerenv'):
            logger.info("stopping container now")
            misc.closeContainer()


    else:
        logger.info("candle data already exists. skipping download")


def download_candlestick_data():
    # download_monthly_futures('NIFTY', 'NFO')

    if datetime.now().weekday() >= 5:
        logger.info("weekday, skipping candle download")
        return

    getOrderBook()

    scheduler = BackgroundScheduler()

    now = datetime.now()
    target_time = now.replace(hour=15, minute=31, second=0)

    if now >= target_time:
        logger.info("downloading candlestick data")
        scheduler.add_job(downloadCheck, 'date', run_date=now + timedelta(seconds=1), misfire_grace_time=30)
        # scheduler.add_job(getOrderBook, 'date', run_date=now + timedelta(seconds=1))

    else:
        # Otherwise, schedule the task to run at the next 2 PM
        logger.info(f"adding job to download candlestick data for {target_time.strftime('%r')}")
        scheduler.add_job(downloadCheck, 'date', run_date=target_time, misfire_grace_time=30)
        # scheduler.add_job(getOrderBook, 'date', run_date=target_time)

    scheduler.start()



# %%
# rclone.copy(out_folder,'googledrive:shoonya/intraday_candle_recorder', ignore_existing=True, args=['--create-empty-src-dirs'])


