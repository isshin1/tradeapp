from fastapi import WebSocket
import json
from queue import Queue
from conf.logging_config import logger
from typing import List
import asyncio
import threading


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.queue = Queue()
        self.background_task = None
        self._event_loop = None
        self._lock = threading.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

        # Start the background task if it's not already running
        if self.background_task is None or self.background_task.done():
            self._event_loop = asyncio.get_running_loop()
            self.background_task = self._event_loop.create_task(self.process_queue_continuous())

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str):
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                logger.error(f"Failed to send message to client: {e}")
                dead_connections.append(connection)

        # Clean up any dead connections
        for connection in dead_connections:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

    def queue_message(self, message):
        """Thread-safe method to add a message to the queue"""
        try:
            self.queue.put(message)
            # Ensure the processing task is running
            self.ensure_queue_processing()
        except Exception as e:
            logger.error(f"Failed to queue message: {message} {e}")

    def ensure_queue_processing(self):
        """Ensures the queue processing task is running correctly"""
        with self._lock:
            # Only create a new task if we have an event loop and the task isn't running
            if self._event_loop is not None and (self.background_task is None or self.background_task.done()):
                try:
                    self.background_task = self._event_loop.create_task(self.process_queue_continuous())
                except RuntimeError as e:
                    logger.error(f"Failed to create queue processing task: {e}")

    async def process_queue_continuous(self):
        """Continuously process messages from the queue"""
        logger.debug("Starting background queue processing task")
        while True:
            try:
                if not self.queue.empty():
                    next_message = self.queue.get()
                    if next_message:
                        await self.send_message(next_message)
                        logger.debug(f"Sent message: {next_message}")
                else:
                    # No messages in queue, sleep briefly to avoid CPU spinning
                    await asyncio.sleep(0.01)

                # If no connections, sleep a bit longer
                if not self.active_connections:
                    await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error processing queue: {e}")
                await asyncio.sleep(0.1)  # Sleep to avoid tight loop on errors


# Singleton instance
connection_manager = ConnectionManager()


def send_message(message):
    """Thread-safe function to send WebSocket messages"""
    connection_manager.queue_message(message)

def send_toast(title, description):
    res = {
        "type": "toast",
        "title": title,
        "description": description
    }
    send_message(json.dumps(res))

def send_price_feed(token, epoch, price):
    res = {
        "type": "price",
        "token": token,
        "tt": epoch,
        "price": price
    }
    send_message(json.dumps(res))

def update_atm_options(ce_token, ce_tsym, pe_token, pe_tsym):
    res = {
        "type": "atm",
        "ceToken": int(ce_token),
        "peToken": int(pe_token),
        "ceTsym": ce_tsym,
        "peTsym": pe_tsym
    }
    print(res)
    send_message(json.dumps(res))

def update_order_feed(orders):
    res = {
        "type": "order",
        "orders": orders
    }
    send_message(json.dumps(res))

def update_position_feed(positions):
    res = {
        "type": "position",
        "positions": positions
    }
    send_message(json.dumps(res))

def update_timer(timer):
    res = {
        "type": "timer",
        "left": timer
    }
    send_message(json.dumps(res))

# Called for every client connecting (after handshake)
def new_client(client, server):
    print(f"New client connected and was given id {client['id']}")

# Called for every client disconnecting
def client_left(client, server):
    print(f"Client {client['id']} disconnected")
