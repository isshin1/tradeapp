# from services import tradeManagement
# from dhanhq import  orderupdate
from conf.logging_config import logger
from Dependencies.dhanhq import orderupdate
import threading
import time


''' 
subscribe to dhan order websocketService.py 
'''
class DhanWebsocket:
    def __init__(self, client_id, access_token, tradeManagement):
        self.client_id = client_id
        self.access_token = access_token
        self.tradeManagement = tradeManagement

    def run_order_update(self):
        order_client = orderupdate.OrderSocket(self.client_id, self.access_token)
        order_client.on_update = self.tradeManagement.on_order_update
        # order_client.connect_to_dhan_websocket_sync()
        while True:
            try:
                order_client.connect_to_dhan_websocket_sync()
            except Exception as e:
                logger.error(f"Error connecting to Dhan WebSocket: {e}. Reconnecting in 5 seconds...")
                time.sleep(5)

    def start_dhan_websocket(self):
        # Create and start a daemon thread so that it won't block shutdown.
        thread = threading.Thread(target=self.run_order_update, daemon=True)
        thread.start()
        logger.info(f"dhan websocketService.py started")