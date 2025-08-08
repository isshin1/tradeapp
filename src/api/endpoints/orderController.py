from fastapi import APIRouter, HTTPException
from conf.config import orderManagement, shoonyaWebsocket, tradeManagement
from pydantic import BaseModel
from conf.config import logger
router = APIRouter()

class TargetRequest(BaseModel):
    t1: float
    t2: float
    # t3: float


@router.post("/api/tradeManagement.updateTargets")
async def update_targets(target_data: TargetRequest):
    try:
        # Extract target values from the request
        t1 = target_data.t1
        t2 = target_data.t2
        # t3 = target_data.t3

        # Process the target updates
        targets = dict()
        targets['t1'] = t1
        targets['t2'] = t2
        # targets['t3'] = t3
        tradeManagement.updateTargets(targets)

        # if result:
        #     return {"success": True, "message": "Your targets have been successfully updated."}
        # else:
        #     raise HTTPException(status_code=500, detail="Failed to update targets")
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=f"Error updating targets: {str(e)}")


@router.post("/api/orderManagement.buyOrder/{token}/{priceType}/{price}/{bof}")
async def buy_order(token: str, priceType: str, price: float, bof: bool):
    try:
        orderManagement.buyOrder(tradeManagement.ltps, token, priceType, price, bof)
        # You can process 'res' if needed; here we simply return a success message.
        return {"message": "order placed"}
    except Exception as e:
        logger.error(f"error in placing order {e}")
        # Raise an HTTPException if there's an error in processing the order
        return HTTPException(status_code=500, detail=str(e))

@router.post("/api/orderManagement.cancelOrder/{orderId}")
async def buy_order(orderId: int):
    return orderManagement.cancelOrder(orderId)
    # return dhan_api.cancel_order(orderId)

@router.post("/api/modifyOrder/{orderId}/{newPrice}")
async def modifyOrder(orderId: int, newPrice: float):
    return orderManagement.modifyActiveOrder(orderId, newPrice)

@router.get("/api/getOrders")
async def getOrders():
    return orderManagement.getOrderBook()






