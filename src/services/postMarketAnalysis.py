from conf.config import logger, order_folder
from datetime import datetime, timedelta
import pandas as pd
from services.test_tradeManagement import run



# class PostMarketAnalysis:
#     def __init__(self):
#         pass

    # @router.post("/api/tradeCheckOld")
    # async def tradeCheck(background_tasks: BackgroundTasks, trade: TradeRequest):
    #     trade.to_datetime()
    #     # token = trade.token
    #
    #     time = trade.time
    #     expiry = trade.expiry
    #     dps = trade.dps
    #
    #     # tsym = 'NIFTY ' +  expiry.strftime('%d %b ').upper() + str(strike_price) +  ' ' +optionType
    #     tsym = trade.tsym
    #     run(time, expiry, tsym, dps)
    #     # background_tasks.add_task(run,  time, expiry , tsym, dps)
    #
    #     return {"message": "Trade started, not waiting for completion"}

def getExpiryFromTsym( tsym):
    parts = tsym.split()
    day = parts[1]
    month = parts[2]

    # Use current year from a datetime object
    current_year = datetime.now().year  # or use your custom datetime.year

    # Parse the date
    date_obj = datetime.strptime(f"{day} {month} {current_year}", "%d %b %Y")

    # Convert to ISO format
    # iso_date_str = date_obj.strftime("%Y-%m-%dT%H:%M:%S")
    return date_obj

def getExpiryFromTsymFolder(tsym:str):
    # tsym = 'NIFTY 29 MAY 24900 CALL'
    _, day, month_str, _, _ = tsym.split(' ')
    month = datetime.strptime(month_str, "%b").strftime("%m")
    # "2025-05-22T00:00:00"
    expiry_str = f"2025-{month}-{day}T00:00:00"
    expiry = datetime.fromisoformat(expiry_str)
    return expiry

def trailTrades(days=0):
    # orderFile = order_folder + str(datetime.now().date()) + '.csv'
    orderFile = order_folder + str((datetime.now() - timedelta(days=days)).date()) + '.csv'

    df = pd.read_csv(orderFile)
    df['exchangeTime'] = pd.to_datetime(df['exchangeTime'])
    df = df.sort_values(by='exchangeTime', ascending=True)

    day_points = []
    for i, row in df.iterrows():
        if row['transactionType'] == 'BUY':
            _, _,_, tsym, time, _, price  = row
            # expiry = getExpiryFromTsym(tsym) # revert it back
            expiry = getExpiryFromTsymFolder(tsym)
            points = run(time,expiry, tsym, [] )
            day_points.append(points)
                # df['trailPoints'] =
    i = 1
    for points in day_points:
        print(i, points)
        i += 1
# trailTrades()

# postMarketAnalysis = PostMarketAnalysis()
# postMarketAnalysis.trailTrades()