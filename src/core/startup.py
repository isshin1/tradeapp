import json
from datetime import datetime
import os
import sys
from typing import Optional, Dict, Any, Callable
import copy
import pyotp
# from Dependencies.dhanhq import DhanContext, dhanhq

from dhanhq import DhanContext, dhanhq
from fastapi import HTTPException
import requests

from conf.config import BASE_DIR, get_date_folders, config
from conf.dhanWebsocket import DhanWebsocket
from conf.logging_config import logger
from conf.shoonyaWebsocket import ShoonyaWebsocket
from conf.websocketService import ConnectionManager
from models.DecisionPoints import DecisionPoints
from models.TradeManager import TradeManager
from services.candleDownload import CandleDownload
from services.optionUpdate import OptionUpdate
from services.orderManagement import OrderManagement
from services.riskManagement import RiskManagement
from services.tradeManagement import TradeManagement
from utils.dhanHelper import DhanHelper, DhanAuthAutomation
from utils.shoonyaHelper import ShoonyaHelper
from utils.misc import Misc
from utils.shoonyaApiHelper import ShoonyaApiPy
from utils.flattradeApiHelper import NorenApiPy
from utils.flattradeApiHelper import FlattradeAuthAutomation
class DIContainer:
    """Simple Dependency Injection Container"""

    def __init__(self):
        self._services = {}
        self._factories = {}
        self._singletons = {}

    def register_factory(self, service_name: str, factory: Callable):
        """Register a factory function for a service"""
        self._factories[service_name] = factory

    def register_singleton(self, service_name: str, instance: Any):
        """Register a singleton instance"""
        self._singletons[service_name] = instance

    def get(self, service_name: str):
        """Get a service instance"""
        if service_name in self._singletons:
            return self._singletons[service_name]

        if service_name in self._factories:
            # Create and cache as singleton
            instance = self._factories[service_name]()
            self._singletons[service_name] = instance
            return instance

        raise ValueError(f"Service '{service_name}' not registered")


class AppInitializer:
    """Application initializer class with dependency injection support"""

    def __init__(self, di_container: Optional[DIContainer] = None):
        self.di_container = di_container or DIContainer()
        self.is_initialized = False

    def setup_directories(self):
        """Create necessary directories for the application"""
        folders = get_date_folders()
        for folder_type, folder_path in folders.items():
            os.makedirs(folder_path, exist_ok=True)
            logger.info(f"Created/verified {folder_type} folder: {folder_path}")

    def setup_python_path(self):
        """Ensure BASE_DIR is in Python path"""
        if BASE_DIR not in sys.path:
            sys.path.append(BASE_DIR)
            logger.info(f"Added to sys.path: {BASE_DIR}")

    def _create_shoonya_api(self, cred):
        """Factory method to create Shoonya API client"""
        try:
            shoonya_api = ShoonyaApiPy()
            cred = config['shoonya']
            totp = pyotp.TOTP(cred['totp_key']).now()
            ret = shoonya_api.login(userid=cred['user'], password=cred['pwd'], twoFA=totp,
                                    vendor_code=cred['vc'], api_secret=cred['api_key'], imei=cred['imei'])
            if ret is None:
                raise Exception(f"Shoonya Login failed")
            logger.info("Shoonya API client created successfully")
            return shoonya_api
        except Exception as e:
            logger.error(f"Failed to create Shoonya API client: {e}")
            # return self._create_flattrade_api()
            raise

    def _create_shoonya_helper(self):
        """Factory method to create Dhan API client"""
        try:
            shoonya_api = self.di_container.get('shoonya_api')
            dhanHelper = ShoonyaHelper(shoonya_api)
            logger.info("Shoonya Helper client created successfully")
            return dhanHelper
        except Exception as e:
            logger.error(f"Failed to create Shoonya helper client: {e}")
            raise

    def _create_dhan_helper(self):
        """Factory method to create Dhan API client"""
        try:
            dhan_api = ""
            dhanHelper = DhanHelper(dhan_api)
            logger.info("Dhan Helper client created successfully")
            return dhanHelper
        except Exception as e:
            logger.error(f"Failed to create Dhan helper client: {e}")
            raise

    def setup_dhan_services(self, config):
        """Setup Dhan context and API client"""
        try:

            self.dhan_helper = self._create_dhan_helper()
            self.di_container.register_singleton('dhan_helper', self.dhan_helper)

            logger.info("Dhan services setup completed and registered in DI container")

        except Exception as e:
            logger.error(f"Failed to setup Dhan services: {e}")
            raise

    def setup_shoonya_services(self, cred):
        self.shoonya_api = self._create_shoonya_api(cred)
        self.di_container.register_singleton('shoonya_api', self.shoonya_api)

        self.shoonya_helper = self._create_shoonya_helper()
        self.di_container.register_singleton('shoonya_helper', self.shoonya_helper)
        # self.shoonya_helper.killswitch()
        logger.info("Shoonya services setup completed and registered in DI container")

    def setup_flattrade_services(self, cred):
        self.flattrade_api = self._create_flattrade_api(cred)
        self.di_container.register_singleton('flattrade_api', self.flattrade_api)
        self.shoonya_helper = self._create_shoonya_helper()
        self.di_container.register_singleton('flattrade_helper', self.flattrade_helper)
        logger.info("flattrade services setup completed and registered in DI container")

    def _create_database_connection(self, database_url: str):
        """Factory method to create database connection"""
        logger.info(f"Creating database connection to: {database_url}")
        from utils.databaseHelper import DBHelper
        db_helper = DBHelper(db_url=database_url)
        logger.info(f"Created database connection using DBHelper: {database_url}")
        return db_helper

    def _create_option_update_service(self):
        """Factory method to create option update service with all dependencies"""
        try:
            # Get all required dependencies
            logger.info("Creating OptionUpdateService with all dependencies")

            # return OptionUpdate(config, dhan_api, misc, trade_management,  trade_manager)
            return OptionUpdate(self.di_container)
        except Exception as e:
            logger.error(f"Failed to create OptionUpdateService: {e}")
            raise

    def _create_shoonya_websocket(self):
        print("Testing shoonya_websocket creation...")
        config = self.di_container.get('config')

        try:
            self.shoonya_ws = ShoonyaWebsocket(self.di_container)
            self.shoonya_ws.start_shoonya_websocket()
            logger.info("Shoonya WebSocket services started successfully")
            return self.shoonya_ws
        except Exception as e:
            logger.error(f"Failed to initialize Shoonya WebSocket: {e}")
            raise

    def _create_dhan_websocket(self):
        print("Testing dhan_websocket creation...")
        config = self.di_container.get('config')
        """Initialize and start Dhan WebSocket connections"""
        try:
            self.dhan_ws = DhanWebsocket(self.di_container)
            self.dhan_ws.start_dhan_websocket()
            logger.info("Dhan WebSocket services started successfully")
            return self.dhan_ws
        except Exception as e:
            logger.error(f"Failed to initialize Dhan WebSocket: {e}")
            raise


    def _download_candles(self):
        print("Starting Candle Download Scheduler...")
        config = self.di_container.get('config')

        try:
            self.shoonya_api = self.di_container.get('shoonya_api')
            self.candle_download = CandleDownload(self.di_container)
            self.candle_download.download_candlestick_data()
            logger.info("Candle Download Scheduler started successfully")
            return self.candle_download
        except Exception as e:
            logger.error(f"Failed to initialize Candle Download Scheduler: {e}")
            raise


    def _get_config(self):
        # dhan_helper = self.di_container.get('dhan_helper')

        config_copy = copy.deepcopy(self.di_container.get('basic_config'))

        config_copy['nifty_symbol'] = 'Nifty 50'
        config_copy['nifty_token'] = '26000'

        misc = self.di_container.get('misc')
        # nifty_monthly_expiry = dhan_helper.get_monthly_expiry('13', "IDX_I", 0)
        nifty_monthly_expiry = misc.get_nse_monthly_expiry(symbol="NIFTY", exchange='NFO', instrument = 'FUTIDX')
        nifty_weekly_expiry = misc.get_nse_weekly_expiry(symbol="NIFTY", exchange='NFO', instrument = 'OPTIDX')
        
        nifty_fut_symbol = "NIFTY" + datetime.strftime(nifty_monthly_expiry, " %b ").upper() + "FUT"
        nifty_fut_symbol_shoonya = "NIFTY" + nifty_monthly_expiry.strftime("%d%b%y").upper() + "F"
        config_copy['nifty_fut_symbol'] = nifty_fut_symbol
        config_copy['nifty_fut_token'] = str(misc.getToken(tsym = nifty_fut_symbol_shoonya, exchange = 'NFO' ))

        config_copy['nifty_monthly_expiry'] = nifty_monthly_expiry
        config_copy['nifty_weekly_expiry'] = nifty_weekly_expiry



        return config_copy

    def _create_misc(self):
        basic_config = self.di_container.get('basic_config')
        return Misc(basic_config)

    def register_dependencies(self, config: Dict[str, Any]):
        """Register all dependencies in the DI container"""
        # Register configuration as singleton

        # Register database connection factory
        if 'database_url' in config:
            self.di_container.register_factory('db_helper',
                                               lambda: self._create_database_connection(config['database_url']))

        # create managers
        try:

            self.di_container.register_singleton('basic_config', config)

            self.di_container.register_factory('misc',
                                               lambda: self._create_misc())

            self.di_container.register_factory('config', lambda: self._get_config())
            self.di_container.register_factory('option_update_service',
                                               lambda: self._create_option_update_service())
            self.di_container.register_factory('shoonya_websocket',
                                                 lambda: self._create_shoonya_websocket())
            self.di_container.register_factory('dhan_websocket',
                                                 lambda: self._create_dhan_websocket())
            self.di_container.register_factory('candle_download',
                                                 lambda: self._download_candles()
                                                 )
        except Exception as  e:
            print(f"Registration failed: {e}")
            import traceback
            traceback.print_exc()  # This will show the full error
            raise
        logger.info("All dependencies registered successfully")


    def initialize_app(self, config: Dict[str, Any]):
        """Initialize application with dependency injection"""
        try:
            # Setup basic infrastructure
            self.setup_directories()
            self.setup_python_path()

            self.setup_shoonya_services(config['shoonya'])
            # Register all dependencies
            self.register_dependencies(config)

            self.is_initialized = True
            logger.info("Application initialization complete with dependency injection")

        except Exception as e:
            logger.error(f"Application initialization failed: {e}")
            raise

    def get_service(self, service_name):
        return self.di_container.get(service_name)

    def get_service_dependency(service_name: str):
        """Generic dependency function for any service"""

        def dependency():
            try:
                return app_initializer.get_service(service_name)
            except ValueError as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Service '{service_name}' not available: {e}"
                )

        return dependency

# Create DI container and app initializer
di_container = DIContainer()
app_initializer = AppInitializer(di_container)