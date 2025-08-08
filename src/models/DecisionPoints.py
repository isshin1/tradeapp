from conf.logging_config import logger
from utils.databaseHelper import db_helper
from sqlalchemy.orm import  Session
from fastapi import Depends
from datetime import datetime
from typing import List

class DecisionPoint:
    def __init__(self, name:str, price:float, call=True, put=True):
        self.name = name
        self.price = price
        self.call = call
        self.put = put
        self.date = datetime.now().date()

class DecisionPoints:
    def __init__(self):
        self.date = datetime.now().date()
        self.decisionPoints = []
        self.get_dps_from_db()

    def addDecisionPoint(self, price, name):
        # Check if a decisionPoint with the same name exists
        try:
            name = name.upper()
            flag = False
            for decisionPoint in self.decisionPoints:
                if decisionPoint.name == name and name != 'BRN':
                    # Update the price if the decisionPoint exists
                    decisionPoint.price = price
                    flag = True
                    break
                if name == 'BRN' and price == decisionPoint.price:
                    flag = True
                    break
                # if decisionPoint.price == price:
                #     # Update the price if the decisionPoint exists
                #     decisionPoint.name = name
                #     flag = True
                #     break
            # If it doesn't exist, create a new decisionPoint and add it to the list
            if not flag:
                decisionPoint = DecisionPoint(name, price)
                self.decisionPoints.append(decisionPoint)
            self.upload_dps_to_db()
        except Exception as e:
            logger.error(e)

        #TODO, check before placing the order
    def checkTradeValidity(self, price, type):
        '''
        check if price is close to an untraded decision point or not
        '''
        for decisionPoint in self.decisionPoints:
            if type == 'CALL' and decisionPoint.call and  abs(price - decisionPoint.price) < 25:
                return True
            if type == 'PUT' and decisionPoint.put and  abs(decisionPoint.price - price)  < 25:
                return True
        return False

    #TODO update after buy order is placed
    def updateDecisionPoints(self, price,  type):

        def find_closest_price(dps: List[DecisionPoint], target_price: float, above: bool) -> DecisionPoint:
            if above:
                dps = [dp for dp in dps if dp.price <= target_price]
            else:
                dps = [dp for dp in dps if dp.price >= target_price]

            closest_dp = min(dps, key=lambda item: abs(item.price - target_price))
            return closest_dp


        if type == 'CE' :
            closest_dp = find_closest_price(self.decisionPoints, price, True)
            closest_dp.call = False
        if type == 'PE':
            closest_dp = find_closest_price(self.decisionPoints, price, False)
            closest_dp.put = False

        self.upload_dps_to_db()

    def get_decision_points(self):
        # Convert list of DecisionPoint objects to list of dictionaries
        self.get_dps_from_db()

        decision_points_dict = [
            {
                "name": dp.name,
                "price": dp.price,
                "call": dp.call,
                "put": dp.put
            } for dp in self.decisionPoints
        ]
        return decision_points_dict

    def upload_dps_to_db(self, db: Session = Depends(db_helper.get_db)):
        for dp in self.decisionPoints:
            db_helper.add_or_update_dp(dp)


    #TODO:
    def get_dps_from_db(self):
        dps = db_helper.get_dps(self.date)
        # dp_schemas = [DpSchema.from_orm(dp) for dp in dps]

        def checkIfDpPresent(dp):
            flag = False
            for decisionPoint in self.decisionPoints:
                if (decisionPoint.name == dp.name and decisionPoint.price == dp.price and decisionPoint.name == dp.name
                        and decisionPoint.date == dp.date and decisionPoint.call == dp.call and decisionPoint.put == dp.put):
                    flag = True
                    break
            return flag

        for dp in dps:
            decision_point = DecisionPoint(dp.name, dp.price, dp.call, dp.put)
            if not checkIfDpPresent(decision_point):
                self.decisionPoints.append(decision_point)
        # return dps

    def getTargetPrices(self, ltp, trade):

        def fut_to_options(targets, ltp):
            return [abs(x - ltp) / 2 for x in targets]


        optionType = trade.optionType

        if optionType == 'CALL':
            dps = [dp for dp in self.decisionPoints if dp.price - ltp > 20]
            dps.sort(key=lambda dp: dp.price)
            try:
                if not trade.bof:
                    targets = [dps[0].price, dps[0].price]
                else:
                    targets = [dps[0].price, dps[1].price]
            except IndexError:
                if not trade.bof:
                    targets = [20, 20]
                else:
                    targets = [20, 40]
            return fut_to_options(targets, ltp)

        else:
            dps = [dp for dp in self.decisionPoints if dp.price - ltp < -20]
            dps.sort(key=lambda dp: dp.price, reverse=True)
            try:
                if not trade.bof:
                    targets = [dps[0].price, dps[0].price]
                else:
                    targets = [dps[0].price, dps[1].price]
            except IndexError:
                if not trade.bof:
                    targets = [20, 20]
                else:
                    targets = [20, 40]
            return fut_to_options(targets, ltp)

    def deleteDp(self, name, price):
        for decisionPoint in self.decisionPoints:
            if decisionPoint.name == name and decisionPoint.price == price:
                self.decisionPoints.remove(decisionPoint)
                logger.info(f"dp deleted with name {name} and price {price}")
                db_helper.delete_dp(decisionPoint)
                break

    def updateDp(self, price, new_price):
        for decisionPoint in self.decisionPoints:
            if decisionPoint.price == price:
                db_helper.update_dp_price(decisionPoint, new_price)
                decisionPoint.price = new_price
                logger.info(f"dp {decisionPoint.name }price changed from {price} to { new_price }")
                break

decisionPoints = DecisionPoints()