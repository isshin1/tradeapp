import pandas as pd
from conf.logging_config import logger
from collections import OrderedDict


class CandlestickData:
    def __init__(self):
        self.candlestickData = dict()

    def reset(self):
        self.candlestickData.clear()
        # for token in self.candlestickData:
        #     del self.candlestickData[token]
        pass

    def getTokenDf(self, token):
        token = int(token)
        # df = pd.DataFrame(candlestickData[token])
        try:
            df = pd.DataFrame.from_dict(self.candlestickData[token], orient='index')
            df['time'] = pd.to_datetime(df['time'])
            df.reset_index(drop=True, inplace=True)
        except Exception as e:
            logger.error("error in getting df for token {}".format(token))
            logger.error(e)
            return None
        # if df.empty:
        #     return  pd.DataFrame(columns = ['time', 'open', 'low', 'high', 'close'])
        return df

    def getLatestPrice(self, token):
        try:
            token = int(token)
            tokenCandlestickData = self.candlestickData[token]
            last_key, last_value = tokenCandlestickData.popitem(last=True)
            tokenCandlestickData[last_key] = last_value
        except Exception as e:
            logger.error(e)
            return 0
        return last_value['close']

    def updateTickDataOld(self, token, feed_data):
        try:
            token = int(token)

            if token not in self.candlestickData:
                self.candlestickData[token] = pd.DataFrame(columns = ['time', 'open', 'low', 'high', 'close'])
            token = token
            tick_price = float(feed_data['ltp'])

            tick_timestamp_epoch = feed_data['ft']
            tick_timestamp = pd.to_datetime(int(tick_timestamp_epoch), unit='s')# Localize the timestamp to UTC
            tick_timestamp_utc = tick_timestamp.tz_localize('UTC')
            # Convert the timestamp to IST
            # tick_timestamp_ist = tick_timestamp_utc.tz_convert('Asia/Kolkata')

            df = self.candlestickData[token]

            candle_start = tick_timestamp.floor('3T')
            # candle_end = candle_start + pd.Timedelta(minutes=3)

            # if candle_start in df.time:
            if (df['time'] == candle_start).any() :

                # Update existing candle
                df.at[candle_start, 'high'] = max(df.at[candle_start, 'high'], tick_price)
                df.at[candle_start, 'low'] = min(df.at[candle_start, 'low'], tick_price)
                df.at[candle_start, 'close'] = tick_price
            else:
                # Create a new 3-minute candle
                new_candle = pd.DataFrame({
                    'time': [candle_start],
                    'open': [tick_price],
                    'high': [tick_price],
                    'low': [tick_price],
                    'close': [tick_price],
                })
                # new_candle.set_index('time', inplace=True)
                # Append and sort DataFrame
                self.candlestickData[token] = pd.concat([df, new_candle]).sort_index()
                # pass
        except Exception as e:
            logger.error(e)

    def updateTickData(self, token, feed_data):
        try:
            token = int(token)
            price = float(feed_data['ltp'])

            tick_timestamp_epoch = feed_data['ft']
            tick_timestamp = pd.to_datetime(int(tick_timestamp_epoch), unit='s')# Localize the timestamp to UTC
            tick_timestamp_utc = tick_timestamp.tz_localize('UTC')
            # Convert the timestamp to IST
            # tick_timestamp_ist = tick_timestamp_utc.tz_convert('Asia/Kolkata')

            candle_start = tick_timestamp.floor('3T').strftime('%Y-%m-%dT%H:%M:%S')

            if token not in self.candlestickData:
                self.candlestickData[token] = OrderedDict()

            tokenCandlestickData = self.candlestickData[token]
            if candle_start in tokenCandlestickData:
                tokenCandlestickData[candle_start]['high'] = max(tokenCandlestickData[candle_start]['high'], price)
                tokenCandlestickData[candle_start]['low'] = min(tokenCandlestickData[candle_start]['low'], price)
                tokenCandlestickData[candle_start]['close'] = price
            else:
                # Create new candlestick
                tokenCandlestickData[candle_start] = {
                    'time': candle_start,
                    'open': price,
                    'high': price,
                    'low': price,
                    'close': price,
                }
        except Exception as e:
            logger.error(f"error in updating tick data {e}")

    def getMspLow(self, fut_token, trade):
        try:
            fut_token = int(fut_token)
            df = self.getTokenDf(fut_token)
            # filtered_df = df[df['time'] >= trade.startTime].reset_index(drop=True)
            filtered_df = df[df['time'] >= trade.startTime].reset_index(drop=True)
            if filtered_df is None or filtered_df.empty or len(filtered_df) < 4:
                return None

            if trade.optionType == 'CALL':
                peak_idx = filtered_df['high'].idxmax()

                if peak_idx > len(filtered_df) - 4:  # If less than 3 candles to the right
                    peak_idx = len(filtered_df) - 4  # Shift to the last possible index with 3 right candles

                # result_low = 0
                result_low_idx = 0
                for i in range(peak_idx, 2, -1):  # Start from peak_idx and go backwards, at least 3 candles on both sides
                    current_low = filtered_df['low'][i]
                    if current_low < min(filtered_df['low'][i - 3:i]) and current_low < min(filtered_df['low'][i + 1:i + 4]):
                        # result_low = current_low
                        result_low_idx = i
                        break
                return filtered_df['time'][result_low_idx]

            if trade.optionType == 'PUT':
                bottom_idx = filtered_df['low'].idxmin()

                if bottom_idx > len(filtered_df) - 4:  # If less than 3 candles to the right
                    bottom_idx = len(filtered_df) - 4  # Shift to the last possible index with 3 right candles

                # result_low = 0
                result_high_idx = 0
                for i in range(bottom_idx, 2, -1):  # Start from bottom_idx and go backwards, at least 3 candles on both sides
                    current_high = filtered_df['high'][i]
                    if current_high > max(filtered_df['high'][i - 3:i]) and current_high > max(filtered_df['high'][i + 1:i + 4]):
                        # result_low = current_low
                        result_high_idx = i
                        return filtered_df.iloc[result_high_idx]['time']
                return filtered_df.iloc[result_high_idx]['time']
        except Exception as e:
            logger.error(f"error in getting msp low {e}")
        return None


    def getCrossedDp(self, ltp, fut_token, decisionPoints, trade):
        fut_token = int(fut_token)
        try:

            df = self.getTokenDf(fut_token)
            filtered_df = df[df['time'] >= trade.startTime].reset_index(drop=True)
            if len(filtered_df) == 0:
                return None, None

            if trade.optionType == 'CALL':
                result_low_date = None
                filtered_dps = [dp for dp in decisionPoints if dp.price < ltp - 15]
            # Find the closest above price

                if len(filtered_dps) == 0:
                    return None, None

                closest_dp = max(filtered_dps, key=lambda dp: dp.price )
                closest_dp_price = closest_dp.price

                result_low_idx = 0

                # df = self.candlestickData[fut_token]
                # df = self.getTokenDf(fut_token)
                # filtered_df = df[df['time'] >= trade.startTime].reset_index(drop=True)
                result_low_date = filtered_df.loc[0, 'time']

                for idx in reversed(filtered_df.index):
                    if filtered_df.loc[idx, 'high'] > closest_dp_price and filtered_df.loc[idx, 'low'] < closest_dp_price:
                        result_low_idx = idx
                        result_low_date = filtered_df.loc[result_low_idx, 'time']
                        break

                return result_low_date,  closest_dp.price

            if trade.optionType == 'PUT':
                filtered_dps = [dp for dp in decisionPoints if dp.price > ltp + 15]
                # Find the closest above price
                if len(filtered_dps) == 0:
                    return None, None

                closest_dp = min(filtered_dps, key=lambda dp: dp.price)
                closest_dp_price = closest_dp.price


                # df = self.getTokenDf(fut_token)
                # filtered_df = df[df['time'] >= trade.startTime].reset_index(drop=True)
                result_low_date = filtered_df.loc[0, 'time']

                for idx in reversed(filtered_df.index):
                    if filtered_df.loc[idx, 'high'] > closest_dp_price and filtered_df.loc[idx, 'low'] < closest_dp_price:
                        result_low_idx = idx
                        result_low_date = filtered_df.loc[result_low_idx, 'time']
                        break

                return result_low_date, closest_dp.price

        except Exception as e:
            logger.error(e)



candlestickData = CandlestickData()

# test code
# from random import random
# token = '26000'
# feed = {'Tsym': 'Nifty 50', 'ltp': 23463.95, 'tt': '2025-03-22T10:35:52', 'ft': 1742621464}
# current_epoch = datetime.now().timestamp()
# for i in range(1, 60):
#     feed = {'Tsym': 'Nifty 50', 'ltp': 23400 + 100 * random(), 'tt': '2025-03-22T10:35:52', 'ft': current_epoch + i * 15}
#     candlestickData.updateTickData(token, feed)
#
