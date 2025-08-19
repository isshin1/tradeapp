from fastapi import APIRouter, HTTPException
from conf.config import orderManagement,  tradeManagement
from conf.config import logger
router = APIRouter()






@router.post("/api/buyOrder/{token}/{priceType}/{price}/{bof}")
async def buy_order(token: str, priceType: str, price: float, bof: bool):
    try:
        orderManagement.buyOrder( token, priceType, price, bof)
        # You can process 'res' if needed; here we simply return a success message.
        return {"message": "order placed"}
    except Exception as e:
        logger.error(f"error in placing order {e}")
        # Raise an HTTPException if there's an error in processing the order
        return HTTPException(status_code=500, detail=str(e))

@router.post("/api/cancelOrder/{orderId}")
async def buy_order(orderId: int):
    return orderManagement.cancelOrder(orderId)
    # return dhan_api.cancel_order(orderId)

@router.post("/api/modifyOrder/{orderId}/{newPrice}")
async def modifyOrder(orderId: int, newPrice: float):
    return orderManagement.modifyActiveOrder(orderId, newPrice)

@router.get("/api/getOrders")
async def getOrders():
    return orderManagement.getOrderBook()






