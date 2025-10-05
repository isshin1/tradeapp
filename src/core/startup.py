import json
from datetime import datetime
import os
import sys
from typing import Optional, Dict, Any, Callable

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
from services.optionUpdate import OptionUpdate
from services.orderManagement import OrderManagement
from services.riskManagement import RiskManagement
from services.tradeManagement import TradeManagement
from utils.dhanHelper import DhanHelper, DhanAuthAutomation
from utils.shoonyaHelper import ShoonyaHelper
from utils.misc import Misc
from utils.shoonyaApiHelper import ShoonyaApiPy

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
        self.dhan_ws = None
        self.trade_management = None
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

    def _create_dhan_context(self, client_id: str, access_token: str):
        """Factory method to create Dhan context"""
        try:
            dhan_context = DhanContext(client_id, access_token)
            logger.info("Dhan context created successfully")
            return dhan_context
        except Exception as e:
            logger.error(f"Failed to create Dhan context: {e}")
            raise

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
            logger.error(f"Failed to create Dhan API client: {e}")
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

    def _create_dhan_api(self, dhan_context):
        """Factory method to create Dhan API client"""

        def checkTokenValidity( token):
            url = 'https://api.dhan.co/v2/profile'
            headers = {'access-token': token}

            response = requests.get(url, headers=headers)
            res = response.json()
            if 'errorType' in res:
                logger.error("Token is invalid")
                raise ValueError("access token is invalid")
            logger.info(response.status_code)

        try:
            dhan_api = dhanhq(dhan_context)
            checkTokenValidity(dhan_context.access_token)
            logger.info("Dhan API client created successfully")
            return dhan_api
        except Exception as e:
            logger.error(f"Failed to create Dhan API client: {e}")
            raise

    def _get_dhan_access_token(self, config, token_id):
        """Get Dhan access token using client credentials flow"""

        app_id = str(config['app_id'])
        app_secret = str(config['app_secret'])

        try:
            url = f"https://auth.dhan.co/app/consumeApp-consent?tokenId={token_id}"
            headers = {
                "app_id": app_id,
                "app_secret": app_secret
            }
            response = requests.post(url, headers=headers)
            response = response.json()
            return response['accessToken']
        except Exception as e:
            logger.error(f"Failed to create Dhan helper client: {e}")
            raise

    def _create_dhan_helper(self):
        """Factory method to create Dhan API client"""
        try:
            dhan_api = self.di_container.get('dhan_api')
            dhanHelper = DhanHelper(dhan_api)
            logger.info("Dhan Helper client created successfully")
            return dhanHelper
        except Exception as e:
            logger.error(f"Failed to create Dhan helper client: {e}")
            raise

    def _get_concent_id(self, client_id, app_id, app_secret):
        url = f"https://auth.dhan.co/app/generate-consent?client_id={client_id}"

        headers = {
            "app_id": app_id,
            "app_secret": app_secret
        }

        response = requests.post(url, headers=headers)

        consentAppId = response.json()['consentAppId']
        return consentAppId

    def _get_dhan_access_token_id(self, config):

        client_id = str(config['client_id'])
        app_id = str(config['app_id'])
        app_secret = str(config['app_secret'])
        phone_number = str(config['phone_number'])
        totp_secret = str(config['totp_secret'])
        pin = str(config['pin'])

        consentAppId = self._get_concent_id(client_id, app_id, app_secret)
        automation = DhanAuthAutomation(headless=True)
        token_id = automation.get_auth_token(
            login_url=f"https://auth.dhan.co/login/consentApp-login?consentAppId={consentAppId}",
            mobile_number=phone_number,
            totp_secret=totp_secret,
            pin=pin
        )
        return token_id

    def setup_dhan_services(self, config):
        """Setup Dhan context and API client"""
        try:
            # Create and store Dhan context
            client_id = str(config['client_id'])
            # access_token = str(config.get('access_token')) or self._get_dhan_access_token(app_id, app_secret, token_id)
            token_id = self._get_dhan_access_token_id(config)

            access_token = str(config.get('access_token', ''))
            if access_token == '':
                access_token = self._get_dhan_access_token(config, token_id)
            self.dhan_context = self._create_dhan_context(client_id, access_token)
            self.dhan_api = self._create_dhan_api(self.dhan_context)

            self.di_container.register_singleton('dhan_context', self.dhan_context)
            self.di_container.register_singleton('dhan_api', self.dhan_api)

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

    def _create_database_connection(self, database_url: str):
        """Factory method to create database connection"""
        logger.info(f"Creating database connection to: {database_url}")
        from utils.databaseHelper import DBHelper
        db_helper = DBHelper(db_url=database_url)
        logger.info(f"Created database connection using DBHelper: {database_url}")
        return db_helper


    def _create_redis_connection(self, redis_url: str):
        """Factory method to create Redis connection"""
        # Your Redis connection logic here
        logger.info(f"Creating Redis connection to: {redis_url}")
        # return redis.from_url(redis_url)
        return f"Redis_Connection({redis_url})"  # Placeholder

    def _create_trade_manager(self):
        logger.info("Creating TradeManager")
        return TradeManager()

    def _create_connection_manager(self):
        logger.info("Creating ConnectionManager")
        return ConnectionManager()

    def _create_decision_points_manager(self):
        logger.info("Creating Decision points manager")
        db_helper = self.di_container.get('db_helper')
        return DecisionPoints(db_helper)

    def _create_risk_management_service(self):
        """Factory method to create risk management service"""
        logger.info("Creating RiskManagementService with dependencies")
        # return RiskManagement(config=config, dhan_api=dhan_api, dhan_helper=dhan_helper)
        return RiskManagement(self.di_container)

    def _create_trade_management_service(self):
        """Factory method to create trade management service with all dependencies"""
        try:
            # Get all required dependencies
            logger.info("Creating TradeManagementService with all dependencies")
            return TradeManagement(self.di_container)
        except Exception as e:
            logger.error(f"Failed to create TradeManagementService: {e}")
            raise

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


    def _create_order_management_service(self):
        """Factory method to create order management service with all dependencies"""
        try:
            # Get all required dependencies
            logger.info("Creating OrderManagementService with all dependencies")

            return OrderManagement(self.di_container)

        except Exception as e:
            logger.error(f"Failed to create OrderManagementService: {e}")
            raise


    def _create_dhan_websocket(self):
        print("Testing dhan_websocket creation...")
        config = self.di_container.get('config')
        """Initialize and start Dhan WebSocket connections"""
        # if not self.trade_management:
        #     # Try to get trade management from DI container
        #     try:
        #         self.trade_management = self.di_container.get('trade_management_service')
        #     except ValueError:
        #         raise ValueError("Trade management service must be registered in DI container")

        try:
            self.dhan_ws = DhanWebsocket(self.di_container)
            self.dhan_ws.start_dhan_websocket()
            logger.info("Dhan WebSocket services started successfully")
            return self.dhan_ws
        except Exception as e:
            logger.error(f"Failed to initialize Dhan WebSocket: {e}")
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


    def _get_config(self):
        # dhan_helper = self.di_container.get('dhan_helper')

        config['nifty_symbol'] = 'Nifty 50'
        config['nifty_token'] = '26000'

        misc = self.di_container.get('misc')
        # nifty_monthly_expiry = dhan_helper.get_monthly_expiry('13', "IDX_I", 0)
        nifty_monthly_expiry = misc.get_nse_monthly_expiry(symbol="NIFTY", exchange='NFO', instrument = 'FUTIDX')

        nifty_fut_symbol = "NIFTY" + datetime.strftime(nifty_monthly_expiry, " %b ").upper() + "FUT"
        nifty_fut_symbol_shoonya = "NIFTY" + nifty_monthly_expiry.strftime("%d%b%y").upper() + "F"
        config['nifty_fut_symbol'] = nifty_fut_symbol
        config['nifty_fut_token'] = str(misc.getToken(tsym = nifty_fut_symbol_shoonya, exchange = 'NFO' ))
        config['nifty_monthly_expiry'] = nifty_monthly_expiry



        return config

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

        # Register Redis connection factory
        # if 'redis_url' in config:
        #     self.di_container.register_factory('redis',
        #                                        lambda: self._create_redis_connection(connection_managerconfig['redis_url']))

        # create managers
        try:

            self.di_container.register_singleton('basic_config', config)

            self.di_container.register_factory('misc',
                                               lambda: self._create_misc())

            self.di_container.register_factory('config', lambda: self._get_config())

            self.di_container.register_factory('trade_manager',
                                               lambda: self._create_trade_manager())
            self.di_container.register_factory('connection_manager',
                                               lambda: self._create_connection_manager())
            self.di_container.register_factory('decision_points_manager',
                                               lambda: self._create_decision_points_manager())

            # create services
            self.di_container.register_factory('risk_management_service',
                                               lambda: self._create_risk_management_service())
            self.di_container.register_factory('trade_management_service',
                                               lambda: self._create_trade_management_service())#
            self.di_container.register_factory('option_update_service',
                                               lambda: self._create_option_update_service())
            self.di_container.register_factory('order_management_service',
                                               lambda: self._create_order_management_service())#
            self.di_container.register_factory('shoonya_websocket',
                                                 lambda: self._create_shoonya_websocket())
            self.di_container.register_factory('dhan_websocket',
                                                 lambda: self._create_dhan_websocket())
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

            self.setup_dhan_services(config['dhan'])
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


    def get_websocket(self):
        """Get the initialized websocket instance"""
        if not self.dhan_ws:
            raise RuntimeError("WebSocket not initialized. Call initialize_websocket first.")
        return self.dhan_ws

    def get_trade_management(self):
        """Get the trade management service instance"""
        if not self.trade_management:
            try:
                self.trade_management = self.di_container.get('trade_management')
            except ValueError:
                raise RuntimeError("Trade management service not registered.")
        return self.trade_management

    def shutdown(self):
        """Clean shutdown of services"""
        try:
            if self.dhan_ws:
                if hasattr(self.dhan_ws, 'stop'):
                    self.dhan_ws.stop()
                logger.info("Dhan WebSocket stopped successfully")

            # Shutdown all services that support it
            for service_name in ['trade_management', 'market_data_service', 'risk_management_service']:
                try:
                    service = self.di_container.get(service_name)
                    if hasattr(service, 'shutdown'):
                        service.shutdown()
                        logger.info(f"{service_name} shutdown successfully")
                except ValueError:
                    continue  # Service not registered

            self.is_initialized = False
            logger.info("Application shutdown complete")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}")




# Create DI container and app initializer
di_container = DIContainer()
app_initializer = AppInitializer(di_container)