import json
from datetime import datetime

class PartialTrade:
    def __init__(self, name, token, status, qty, entryPrice,
                 orderType, exch, tsym, optionType, diff, slPrice=0,  targetPoints=0, maxSlPrice=0,
                  prd='', bof=False, startTime=datetime.now()):
        self.name = name
        self.status = status  # 0:inactive, 1:active, 2:completed
        self.qty = qty
        self.entryPrice = entryPrice
        self.exitPrice = None
        self.slPrice = slPrice
        self.maxSlPrice = maxSlPrice
        self.targetPoints = targetPoints
        self.orderNumber = None
        # self.targetOrderNumbers = [None] * 2
        self.orderType = orderType
        self.prd = prd
        self.exch = exch
        self.tsym = tsym
        self.diff = diff
        self.token = token
        self.bof = bof
        self.optionType = optionType
        self.startTime = startTime
        self.dpsCrossed = []

    def __str__(self):
        return json.dumps({
            "name": self.name,
            "token": self.token,
            "status": self.status,
            "qty": self.qty,
            "entryPrice": self.entryPrice,
            "exitPrice": self.exitPrice,
            "slPrice": self.slPrice,
            "maxSlPrice": self.maxSlPrice,
            "targetPoints": self.targetPoints,
            # "targetQtys": self.targetQtys,
            "orderNumber": self.orderNumber,
            # "targetOrderNumbers": self.targetOrderNumbers,
            "orderType": self.orderType,
            "prd": self.prd,
            "exch": self.exch,
            "tsym": self.tsym,
            "diff": self.diff,
            "bof": self.bof,
            "optionType": self.optionType,
            "startTime": self.startTime.strftime('%Y-%m-%d %H:%M:%S')
        }, indent=4)

    # def update_from_dict(self, data):
    #     self.name = data.get("name", self.name)
    #     self.token = data.get("token", self.token)
    #     self.status = data.get("status", self.status)
    #     self.qty = data.get("qty", self.qty)
    #     self.entryPrice = data.get("entryPrice", self.entryPrice)
    #     self.exitPrice = data.get("exitPrice", self.exitPrice)
    #     self.slPrice = data.get("slPrice", self.slPrice)
    #     self.maxSlPrice = data.get("maxSlPrice", self.maxSlPrice)
    #     self.targetPointss = data.get("targetPointss", self.targetPointss)
    #     self.targetQtys = data.get("targetQtys", self.targetQtys)
    #     self.orderNumber = data.get("orderNumber", self.orderNumber)
    #     self.targetOrderNumbers = data.get("targetOrderNumbers", self.targetOrderNumbers)
    #     self.orderType = data.get("orderType", self.orderType)
    #     self.prd = data.get("prd", self.prd)
    #     self.exch = data.get("exch", self.exch)
    #     self.tsym = data.get("tsym", self.tsym)
    #     self.diff = data.get("diff", self.diff)
    #     self.bof = data.get("bof", self.bof)
    #     self.optionType = data.get("optionType", self.optionType)
