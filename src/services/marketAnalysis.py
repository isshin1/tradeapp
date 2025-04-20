from conf.config import *
import pandas as pd
from utils.misc import misc


class MarketAnalysis:

    def getPreviousDayData(self):
        df = misc.fut_df
        today = pd.Timestamp.today().normalize()
        previous_timestamp = df[df['time'] < today]['time'].max()
        previous_date = previous_timestamp.normalize()
        df_previous = df[df['time'].dt.normalize() == previous_date]

        pdh = df_previous['high'].max()
        pdl = df_previous['low'].min()
        pdc = df_previous.iloc[-1]['close']
        logger.info(f"pdh : {pdh} pdl : {pdl} pdc : {pdc}")
        return pdh, pdl, pdc


    def __init__(self):
        self.pdh , self.pdl, self.pdc = self.getPreviousDayData()
    def run(self):
        pass

marketAnalysis = MarketAnalysis()
