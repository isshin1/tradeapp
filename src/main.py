import sys, os
dependencies_path = os.path.join(os.path.dirname(__file__), 'Dependencies')
sys.path.insert(0, dependencies_path)


from fastapi import FastAPI, WebSocket, WebSocketDisconnect,  Depends, HTTPException, Security
from contextlib import asynccontextmanager
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials


from conf.config import *
from conf.logging_config import logger
from api.endpoints import riskController , testController, orderController, pollingController, tradeController
from fastapi.middleware.cors import CORSMiddleware

import uvicorn
import os, stat
from conf.websocketService import connection_manager
from core.startup import app_initializer, di_container
# Initialize the FastAPI app
app = FastAPI()
# Include the routers
app.include_router(riskController.router)
app.include_router(testController.router)
app.include_router(orderController.router)
app.include_router(pollingController.router)

app.include_router(tradeController.router)

# Define the startup function
async def startup_function():
    try:
        # Initialize the application with DI
        app_initializer.initialize_app(config)
        app_initializer.di_container.get('shoonya_websocket')
        app_initializer.di_container.get('candle_download')
        logger.info("Application initialization completed")

    except Exception as e:
        logger.error(f"Startup failed: {e}")
        raise

# Define the shutdown function
async def shutdown_function():
    logger.info("Application is shutting down, enabling killswitch")
    # riskManagement.endSession()
    if os.path.exists('/.dockerenv'):
        mode = 0o777
        path = 'data'
        for root, dirs, files in os.walk(path):
            # Set permission for directories
            for dir_ in dirs:
                full_dir_path = os.path.join(root, dir_)
                os.chmod(full_dir_path, mode)

            # Set permission for files
            for file_ in files:
                full_file_path = os.path.join(root, file_)
                os.chmod(full_file_path, mode)

        # Set permission for the root directory itself
        os.chmod(path, mode)

# Define the lifespan context
@asynccontextmanager
async def lifespan(app: FastAPI):
    await startup_function()
    yield
    await shutdown_function()

# Assign the lifespan context to the app
app.router.lifespan_context = lifespan

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # await websocket.send_text(f"Message text was: {data}")
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        print("Client disconnected")


# Run the FastAPI app with uvicorn
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)