from fastapi import HTTPException
from core.startup import app_initializer

def get_risk_management():
    """Get risk management service"""
    try:
        return app_initializer.get_service('risk_management_service')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Risk management service not available: {e}")

def get_order_management():
    """Get order management service"""
    try:
        return app_initializer.get_service('order_management_service')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Order management service not available: {e}")

def get_trade_management():
    """Get trade management service"""
    try:
        return app_initializer.get_service('trade_management_service')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Trade management service not available: {e}")

def get_dhan_websocket():
    """Get dhan websocket service"""
    try:
        return app_initializer.get_service('dhan_websocket')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"WebSocket service not available: {e}")

def get_shoonya_websocket():
    """Get shoonya websocket service"""
    try:
        return app_initializer.get_service('shoonya_websocket')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"WebSocket service not available: {e}")

def get_option_update_service():
    """Get option update service"""
    try:
        return app_initializer.get_service('option_update_service')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Option update service not available: {e}")

def get_dhan_api():
    """Get Dhan API client"""
    try:
        return app_initializer.get_service('dhan_api')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Dhan API not available: {e}")

def get_dhan_helper():
    """Get Dhan helper"""
    try:
        return app_initializer.get_service('dhan_helper')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Dhan helper not available: {e}")

def get_trade_manager():
    """Get trade manager"""
    try:
        return app_initializer.get_service('trade_manager')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Trade manager not available: {e}")

def get_connection_manager():
    """Get connection manager"""
    try:
        return app_initializer.get_service('connection_manager')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Connection manager not available: {e}")

def get_decision_points_manager():
    """Get decision points manager"""
    try:
        return app_initializer.get_service('decision_points_manager')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Decision points manager not available: {e}")

def get_db_manager():
    """Get decision points manager"""
    try:
        return app_initializer.get_service('db_helper')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"db service not available: {e}")


def get_shoonya_api():
    """Get Shoonya API client"""
    try:
        return app_initializer.get_service('shoonya_api')
    except ValueError as e:
        raise HTTPException(status_code=500, detail=f"Shoonya API not available: {e}")
