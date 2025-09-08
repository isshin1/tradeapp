from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Optional, List, Dict, Any
import logging

# Assuming these imports exist in your project
from models.models import Plan, Dp
# from conf.config import DATABASE_URL

logger = logging.getLogger(__name__)


class DBHelper:
    """Database helper class for managing database operations."""

    def __init__(self, db_url: str = None):
        """
        Initialize database helper.

        Args:
            db_url: Database URL. If None, uses DATABASE_URL from config.
        """
        self.database_url = db_url
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,  # Verify connections before use
            pool_recycle=300,  # Recycle connections every 5 minutes
            echo=False  # Set to True for SQL logging in development
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )

    @contextmanager
    def get_db_session(self):
        """
        Context manager for database sessions.
        Ensures proper cleanup even if exceptions occur.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()

    def get_db(self):
        """
        Generator for dependency injection (FastAPI compatible).
        Use get_db_session() context manager for direct usage.
        """
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    def add_or_update_plan(self, plan_schema, db: Session) -> Plan:
        """
        Add or update a plan for a specific date.
        Args:
            plan_schema: Schema object with date and plan attributes
            db: Database session
        Returns:
            Plan: The created or updated Plan object
        """
        plan = db.query(Plan).filter(Plan.date == plan_schema.date).first()
        if plan:
            plan.plan = plan_schema.plan
            logger.info(f"Updated plan for date {plan_schema.date}")
        else:
            plan = Plan(date=plan_schema.date, plan=plan_schema.plan)
            db.add(plan)
            logger.info(f"Created new plan for date {plan_schema.date}")

        db.commit()
        db.refresh(plan)
        return plan

    def add_or_update_dp(self, dp_schema) -> Dp:
        """
        Add or update a DP (options data) record.

        Args:
            dp_schema: Schema object with date, name, price, call, put attributes

        Returns:
            Dp: The created or updated Dp object
        """
        with self.get_db_session() as db:
            dp = db.query(Dp).filter(
                Dp.date == dp_schema.date,
                Dp.name == dp_schema.name,
                Dp.price == dp_schema.price
            ).first()

            if dp:
                dp.call = dp_schema.call
                dp.put = dp_schema.put
                logger.info(f"Updated DP for {dp_schema.name} on {dp_schema.date}")
            else:
                dp = Dp(
                    date=dp_schema.date,
                    name=dp_schema.name,
                    price=dp_schema.price,
                    call=dp_schema.call,
                    put=dp_schema.put
                )
                db.add(dp)
                logger.info(f"Created new DP for {dp_schema.name} on {dp_schema.date}")

            db.flush()
            db.refresh(dp)
            return dp

    def update_dp_price(self, dp_schema, new_price: float) -> Optional[Dp]:
        """
        Update the price of an existing DP record.

        Args:
            dp_schema: Schema object to identify the DP record
            new_price: New price value

        Returns:
            Dp: Updated Dp object or None if not found
        """
        with self.get_db_session() as db:
            dp = db.query(Dp).filter(
                Dp.date == dp_schema.date,
                Dp.name == dp_schema.name,
                Dp.price == dp_schema.price
            ).first()

            if dp:
                old_price = dp.price
                dp.price = new_price
                dp.call = dp_schema.call
                dp.put = dp_schema.put
                db.flush()
                db.refresh(dp)
                logger.info(f"Updated DP price from {old_price} to {new_price} for {dp_schema.name}")
                return dp
            else:
                logger.warning(f"DP not found for update: {dp_schema.name} on {dp_schema.date}")
                return None

    def delete_dp(self, dp_schema) -> bool:
        """
        Delete a DP record.

        Args:
            dp_schema: Schema object to identify the DP record

        Returns:
            bool: True if deleted, False if not found
        """
        with self.get_db_session() as db:
            dp = db.query(Dp).filter(
                Dp.name == dp_schema.name,
                Dp.price == dp_schema.price
            ).first()

            if dp:
                db.delete(dp)
                logger.info(f"Deleted DP: {dp_schema.name} at price {dp_schema.price}")
                return True
            else:
                logger.warning(f"DP not found for deletion: {dp_schema.name} at price {dp_schema.price}")
                return False

    def get_dps(self, date) -> List[Dp]:
        """
        Get all DP records for a specific date.

        Args:
            date: Date to filter by

        Returns:
            List[Dp]: List of DP objects for the given date
        """
        with self.get_db_session() as db:
            dps = db.query(Dp).filter(Dp.date == date).all()

            # Force load all attributes to avoid DetachedInstanceError
            for dp in dps:
                # Access all attributes to ensure they're loaded
                _ = dp.name, dp.price, dp.call, dp.put, dp.date

            # logger.info(f"Retrieved {len(dps)} DPs for date {date}")
            return dps

    def get_plan(self, date) -> Dict[str, Any]:
        """
        Get plan for a specific date.

        Args:
            date: Date to get plan for

        Returns:
            Dict: Dictionary with date and plan information
        """
        with self.get_db_session() as db:
            plan = db.query(Plan).filter(Plan.date == date).first()

            if plan:
                logger.info(f"Retrieved plan for date {date}")
                return {"date": date, "plan": plan.plan}
            else:
                logger.info(f"No plan found for date {date}")
                return {"date": date, "plan": "no plan for this day"}

    def get_dps_by_name(self, name: str, date: Optional[str] = None) -> List[Dp]:
        """
        Get DP records by name, optionally filtered by date.

        Args:
            name: Name to filter by
            date: Optional date filter

        Returns:
            List[Dp]: List of matching DP objects
        """
        with self.get_db_session() as db:
            query = db.query(Dp).filter(Dp.name == name)
            if date:
                query = query.filter(Dp.date == date)

            dps = query.all()
            # logger.info(f"Retrieved {len(dps)} DPs for name {name}")
            return dps

    def get_dps_as_dict(self, date) -> List[Dict[str, Any]]:
        """
        Get all DP records for a specific date as dictionaries.
        This method avoids DetachedInstanceError by returning plain dictionaries.

        Args:
            date: Date to filter by

        Returns:
            List[Dict]: List of DP data as dictionaries
        """
        with self.get_db_session() as db:
            dps = db.query(Dp).filter(Dp.date == date).all()

            # Convert to dictionaries to avoid DetachedInstanceError
            dp_dicts = []
            for dp in dps:
                dp_dict = {
                    'id': dp.id if hasattr(dp, 'id') else None,
                    'date': dp.date,
                    'name': dp.name,
                    'price': dp.price,
                    'call': dp.call,
                    'put': dp.put
                }
                dp_dicts.append(dp_dict)

            # logger.info(f"Retrieved {len(dp_dicts)} DPs as dicts for date {date}")
            return dp_dicts
#
#
# # Example usage
# if __name__ == "__main__":
#     # Initialize the helper
#     db_helper = DBHelper()
#
#     # Example usage with context manager
#     try:
#         with db_helper.get_db_session() as db:
#             # Your database operations here
#             plans = db.query(Plan).limit(5).all()
#             print(f"Found {len(plans)} plans")
#     except Exception as e:
#         print(f"Error: {e}")
#     finally:
#         db_helper.close()