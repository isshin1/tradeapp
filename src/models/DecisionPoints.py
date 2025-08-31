from conf.logging_config import logger
from sqlalchemy.orm import Session
from fastapi import Depends
from datetime import datetime
from typing import List


class DecisionPoint:
    def __init__(self, name: str, price: float, call=True, put=True):
        self.name = name
        self.price = price
        self.call = call
        self.put = put
        self.date = datetime.now().date()


class DecisionPoints:
    def __init__(self, db_helper):
        self.date = datetime.now().date()
        self.decisionPoints = []
        self.db_helper = db_helper
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
            # If it doesn't exist, create a new decisionPoint and add it to the list
            if not flag:
                decisionPoint = DecisionPoint(name, price)
                self.decisionPoints.append(decisionPoint)
            self.upload_dps_to_db()
        except Exception as e:
            logger.error(e)

    def checkTradeValidity(self, price, type):
        '''
        check if price is close to an untraded decision point or not
        '''
        for decisionPoint in self.decisionPoints:
            if type == 'CALL' and decisionPoint.call and abs(price - decisionPoint.price) < 25:
                return True
            if type == 'PUT' and decisionPoint.put and abs(decisionPoint.price - price) < 25:
                return True
        return False

    def updateDecisionPoints(self, price, type):
        def find_closest_price(dps: List[DecisionPoint], target_price: float, above: bool) -> DecisionPoint:
            if above:
                dps = [dp for dp in dps if dp.price <= target_price]
            else:
                dps = [dp for dp in dps if dp.price >= target_price]

            closest_dp = min(dps, key=lambda item: abs(item.price - target_price))
            return closest_dp

        if type == 'CE':
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

    def upload_dps_to_db(self):
        for dp in self.decisionPoints:
            self.db_helper.add_or_update_dp(dp)

    def get_dps_from_db(self):
        """
        Load decision points from database using dictionary approach to avoid DetachedInstanceError.
        """
        try:
            # Use get_dps_as_dict instead of get_dps to avoid DetachedInstanceError
            dps_data = self.db_helper.get_dps_as_dict(self.date)

            def checkIfDpPresent(dp_dict):
                """Check if a decision point already exists in the list."""
                for decisionPoint in self.decisionPoints:
                    if (decisionPoint.name == dp_dict['name'] and
                            decisionPoint.price == dp_dict['price'] and
                            decisionPoint.date == dp_dict['date'] and
                            decisionPoint.call == dp_dict['call'] and
                            decisionPoint.put == dp_dict['put']):
                        return True
                return False

            # Process each DP from database
            for dp_dict in dps_data:
                if not checkIfDpPresent(dp_dict):
                    # Create DecisionPoint from dictionary data
                    decision_point = DecisionPoint(
                        dp_dict['name'],
                        dp_dict['price'],
                        dp_dict['call'],
                        dp_dict['put']
                    )
                    # Set the date from database instead of current date
                    decision_point.date = dp_dict['date']
                    self.decisionPoints.append(decision_point)

            logger.info(f"Loaded {len(self.decisionPoints)} decision points from database")

        except Exception as e:
            logger.error(f"Error loading decision points from database: {e}")
            # Don't clear existing decision points on error, just log it
            raise

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
                self.db_helper.delete_dp(decisionPoint)
                break

    def updateDp(self, price, new_price):
        for decisionPoint in self.decisionPoints:
            if decisionPoint.price == price:
                self.db_helper.update_dp_price(decisionPoint, new_price)
                decisionPoint.price = new_price
                logger.info(f"dp {decisionPoint.name} price changed from {price} to {new_price}")
                break