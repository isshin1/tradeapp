class TradeManager:
    def __init__(self):
        self.trades = dict()
        # self.trade = None

    def setTrade(self, trade):
        self.trade = trade

    def addTrade(self, token,  partialTrade):
        if token not in self.trades:
            self.trades[token] = {}
        self.trades[token][partialTrade.name] = partialTrade

    def getTrades(self, token):
        return self.trades.get(token, {})

    def removeTrade(self, token):
        if token in self.trades:
            del self.trades[token]
            return True
        return False

    def updatePartialTrade(self,  partialTrade):
        name = partialTrade.name
        token = partialTrade.token
        if token in self.trades:
            self.trades[token][name] = partialTrade

    def hasToken(self, token):
        return token in self.trades

    def isTradeActive(self, token=None):
        if token == None:
            return len(self.trades) > 0
        return token in self.trades

    # def removeTrade(self):
    #     self.trade = None


# tradeManagerDhan = TradeManager()
# tradeManagerShoonya = TradeManager()